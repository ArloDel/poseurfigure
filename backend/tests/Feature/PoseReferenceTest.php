<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Jobs\ReadPoseReference;
use App\Jobs\SearchPoseReferences;
use App\Models\Analysis;
use App\Models\FigureProfile;
use App\Models\PoseReference;
use App\Models\ReferenceSearch;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

/** Pose references from Pinterest (personal instances). The AI service is faked: nothing contacts Pinterest. */
class PoseReferenceTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    /** @var list<array<string, mixed>> */
    private array $inspireCalls = [];

    /** What /v1/references/read answers next (merged over an accepted read). */
    private array $read = [];

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        Storage::fake('s3');
        Storage::disk('s3')->put('analyses/x/photo.jpg', 'photo-bytes');
        $this->guestKey = (string) Str::uuid();
        config(['figurepose.references.pinterest' => true, 'figurepose.references.per_search' => 5]);
    }

    private function fakeAi(array $read = []): void
    {
        $this->inspireCalls = [];
        $this->read = $read;
        Http::fake([
            '*/v1/analyze' => Http::response([
                'model_version' => 'test', 'stage' => 'keypoints', 'profile' => 'humanoid_v1',
                'quality' => ['ok' => true, 'issues' => []],
                'figures' => [['bbox' => [0.2, 0.1, 0.8, 0.95], 'score' => 0.7]], 'selected_figure' => 0,
                'classification' => ['profile' => 'humanoid_v1', 'confidence' => 0.9, 'scores' => [], 'needs_confirmation' => false, 'source' => 'model'],
                'pose' => ['profile' => 'humanoid_v1', 'visible_count' => 16, 'hidden' => [],
                    'keypoints' => ['neck' => ['x' => 0.5, 'y' => 0.2, 'confidence' => 0.9, 'visibility' => 'visible']]],
                'appearance' => ['embedding' => [0.6, 0.8], 'version' => 'test'],
            ]),
            '*/v1/inspire' => function ($request) {
                $this->inspireCalls[] = $sent = $request->data();
                // References (negative ids) first, like same-character ideas.
                $ids = array_column($sent['candidates'], 'id');
                usort($ids, fn ($a, $b) => $a <=> $b);

                return Http::response(['matcher_version' => 'inspire-0.1', 'profile' => 'humanoid_v1', 'basis' => 'pose', 'remaining' => 0,
                    'results' => array_map(fn ($id) => ['id' => $id, 'score' => 0.8, 'similarity' => 0.6, 'feasibility' => 1.0,
                        'components' => [], 'shared_joints' => 12, 'mirrored' => false, 'warnings' => [], 'changes' => [],
                        'reasons' => $id < 0 ? ['same_character'] : ['similar_look'], 'group' => $id < 0 ? 'same_character' : 'similar_look', 'look' => 0.9,
                    ], array_slice($ids, 0, $sent['top_k']))]);
            },
            '*/v1/references/search' => Http::response(['query' => 'q', 'urls' => [
                'https://i.pinimg.com/originals/a.jpg', 'https://i.pinimg.com/originals/b.jpg', 'https://i.pinimg.com/originals/seen.jpg',
            ]]),
            '*/v1/references/read' => fn () => Http::response($this->read + [
                'accepted' => true, 'reason' => null, 'image_base64' => base64_encode('ref-jpeg'), 'width' => 600, 'height' => 900,
                'figure_box' => [0.1, 0.1, 0.9, 0.95], 'keypoints' => ['neck' => ['x' => 0.5, 'y' => 0.2, 'visibility' => 'visible']],
                'joint_angles' => ['left_knee' => 90.0], 'orientation' => 'front', 'visible_count' => 15,
                'appearance' => [0.6, 0.8], 'appearance_version' => 'test',
            ]),
        ]);
    }

    private function analyzed(): Analysis
    {
        $analysis = Analysis::create([
            'guest_key_hash' => Analysis::hashGuestKey($this->guestKey),
            'analysis_mode' => AnalysisMode::Automatic, 'status' => AnalysisStatus::Pending,
            'image_disk' => 's3', 'image_path' => 'analyses/x/photo.jpg', 'image_mime' => 'image/jpeg',
            'image_size' => 5, 'image_width' => 900, 'image_height' => 1200,
        ]);
        app()->call([new ProcessFigureAnalysis($analysis->id), 'handle']);

        return $analysis->fresh();
    }

    private function nameCharacter(Analysis $analysis, string $name)
    {
        return $this->withHeader('X-Guest-Key', $this->guestKey)
            ->putJson("/api/v1/analyses/{$analysis->public_id}/character", ['name' => $name]);
    }

    private function seenBefore(): void
    {
        PoseReference::create(['character_key' => 'spiderman', 'character_name' => 'Spider-Man', 'source' => 'pinterest',
            'source_url' => 'https://i.pinimg.com/originals/seen.jpg', 'source_url_hash' => hash('sha256', 'https://i.pinimg.com/originals/seen.jpg'),
            'status' => 'rejected', 'reject_reason' => 'pose_incomplete']);
    }

    public function test_naming_the_character_starts_one_search_on_the_references_queue(): void
    {
        Queue::fake();
        $this->fakeAi();
        $analysis = $this->analyzed();

        $this->nameCharacter($analysis, 'Spider-Man (symbiote suit)')->assertOk()
            ->assertJsonPath('data.references', ['status' => 'running', 'total' => 0, 'checked' => 0, 'found' => 0, 'error' => null]);
        $this->nameCharacter($analysis, 'spider-man')->assertOk(); // same character: no second search

        Queue::assertPushedOn('references', SearchPoseReferences::class);
        Queue::assertPushed(SearchPoseReferences::class, 1);
        $this->assertSame('spiderman', ReferenceSearch::sole()->character_key);
    }

    public function test_nothing_is_searched_when_the_feature_is_off(): void
    {
        Queue::fake();
        $this->fakeAi();
        config(['figurepose.references.pinterest' => false]);
        $analysis = $this->analyzed();

        $this->nameCharacter($analysis, 'Spider-Man')->assertOk()->assertJsonMissingPath('data.references');
        Queue::assertNothingPushed();
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/v1/references'));
    }

    public function test_the_search_queues_one_read_per_new_image(): void
    {
        Queue::fake();
        $this->fakeAi();
        $this->seenBefore();
        $search = ReferenceSearch::create(['character_key' => 'spiderman', 'character_name' => 'Spider-Man (symbiote suit)',
            'figure_profile_id' => FigureProfile::where('slug', 'humanoid_v1')->value('id'), 'status' => 'running']);

        app()->call([new SearchPoseReferences($search->id), 'handle']);

        Http::assertSent(fn ($r) => str_contains($r->url(), '/v1/references/search') && $r['query'] === 'Spider-Man (symbiote suit) figure' && $r['limit'] === 5);
        $this->assertSame(2, $search->fresh()->total);
        Queue::assertPushed(ReadPoseReference::class, 2);
        Queue::assertPushedOn('references', ReadPoseReference::class);
    }

    public function test_an_accepted_image_becomes_a_same_character_idea_with_a_private_image(): void
    {
        Queue::fake();
        $this->fakeAi();
        $analysis = $this->analyzed();
        $this->nameCharacter($analysis, 'Spider-Man (symbiote suit)');
        $search = ReferenceSearch::sole();
        $search->update(['total' => 2]);

        app()->call([new ReadPoseReference($search->id, 'https://i.pinimg.com/originals/a.jpg'), 'handle']);

        $ref = PoseReference::sole();
        $this->assertSame('accepted', $ref->status);
        Storage::disk('s3')->assertExists($ref->image_path);
        $this->assertSame(['found' => 1, 'checked' => 1, 'status' => 'running'], $search->fresh()->only(['found', 'checked', 'status']));
        // The analysis was ranked again with the reference as a candidate.
        $this->assertContains(-$ref->id, array_column(end($this->inspireCalls)['candidates'], 'id'));

        $data = $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$analysis->public_id}")
            ->assertJsonPath('data.recommendations.0.group', 'same_character')
            ->assertJsonPath('data.recommendations.0.pose.kind', 'reference')
            ->assertJsonPath('data.recommendations.0.pose.source', 'pinterest')
            ->assertJsonPath('data.recommendations.0.pose.name', 'Spider-Man (symbiote suit)')
            ->json('data');

        $url = $data['recommendations'][0]['pose']['image_url'];
        $this->flushHeaders();
        $this->get($url)->assertOk()->assertHeader('Content-Type', 'image/jpeg');
        $this->getJson("/api/v1/pose-references/{$ref->id}/image")->assertForbidden();
    }

    public function test_rejected_and_duplicate_images_are_remembered_and_the_search_finishes(): void
    {
        Queue::fake();
        $this->fakeAi();
        $search = ReferenceSearch::create(['character_key' => 'spiderman', 'character_name' => 'Spider-Man',
            'figure_profile_id' => FigureProfile::where('slug', 'humanoid_v1')->value('id'), 'status' => 'running', 'total' => 3]);

        app()->call([new ReadPoseReference($search->id, 'https://i.pinimg.com/originals/a.jpg'), 'handle']);
        // Same look as the first one: a duplicate.
        app()->call([new ReadPoseReference($search->id, 'https://i.pinimg.com/originals/b.jpg'), 'handle']);
        $this->read = ['accepted' => false, 'reason' => 'pose_incomplete'];
        app()->call([new ReadPoseReference($search->id, 'https://i.pinimg.com/originals/c.jpg'), 'handle']);

        $this->assertSame(['accepted', 'rejected', 'rejected'], PoseReference::orderBy('id')->pluck('status')->all());
        $this->assertSame([null, 'duplicate', 'pose_incomplete'], PoseReference::orderBy('id')->pluck('reject_reason')->all());
        $this->assertSame(['status' => 'done', 'checked' => 3, 'found' => 1], $search->fresh()->only(['status', 'checked', 'found']));
    }

    public function test_a_failed_read_still_counts_so_the_search_can_finish(): void
    {
        $search = ReferenceSearch::create(['character_key' => 'spiderman', 'character_name' => 'Spider-Man', 'status' => 'running', 'total' => 1]);
        (new ReadPoseReference($search->id, 'https://i.pinimg.com/originals/a.jpg'))->failed(new \RuntimeException('down'));
        $this->assertSame('done', $search->fresh()->status);

        (new SearchPoseReferences($search->id))->failed(new \RuntimeException('blocked'));
        $this->assertSame('failed', $search->fresh()->status);
    }
}

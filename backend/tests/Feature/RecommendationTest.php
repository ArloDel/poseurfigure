<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Models\PoseCatalog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class RecommendationTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        Storage::fake('s3');
        Storage::disk('s3')->put('analyses/x/photo.jpg', 'bytes');
        $this->guestKey = (string) Str::uuid();
    }

    private function analysis(array $attrs = []): Analysis
    {
        return Analysis::create($attrs + [
            'guest_key_hash' => Analysis::hashGuestKey($this->guestKey),
            'analysis_mode' => AnalysisMode::Automatic,
            'status' => AnalysisStatus::Pending,
            'image_disk' => 's3', 'image_path' => 'analyses/x/photo.jpg', 'image_mime' => 'image/jpeg',
            'image_size' => 5, 'image_width' => 900, 'image_height' => 1200,
        ]);
    }

    private function analyzeResponse(string $profile = 'humanoid_v1'): array
    {
        return [
            'model_version' => 'pipeline-0.2+test', 'stage' => 'keypoints', 'profile' => $profile,
            'quality' => ['ok' => true, 'issues' => []],
            'figures' => [['bbox' => [0.2, 0.1, 0.8, 0.95], 'score' => 0.7]], 'selected_figure' => 0,
            'classification' => ['profile' => $profile, 'confidence' => 0.9, 'scores' => [], 'needs_confirmation' => false, 'source' => 'model'],
            'pose' => ['profile' => $profile, 'visible_count' => 16, 'hidden' => [],
                'keypoints' => ['neck' => ['x' => 0.5, 'y' => 0.2, 'confidence' => 0.9, 'visibility' => 'visible']]],
        ];
    }

    /** Fake matcher: ranks whatever candidates it receives in reverse id order, with one mirrored warning. */
    private function fakeAi(?array &$sent = null): void
    {
        Http::fake([
            '*/v1/analyze' => Http::response($this->analyzeResponse()),
            '*/v1/recommend' => function ($request) use (&$sent) {
                $sent = $request->data();
                $ids = array_reverse(array_column($sent['candidates'], 'id'));

                return Http::response(['matcher_version' => 'match-0.1', 'profile' => $sent['profile'], 'results' => array_map(
                    fn ($id, $i) => ['id' => $id, 'score' => 0.9 - $i / 10, 'similarity' => 0.8, 'feasibility' => $i === 0 ? 0.7 : 1.0,
                        'components' => ['angle' => 0.8], 'shared_joints' => 12, 'mirrored' => $i === 0,
                        'warnings' => $i === 0 ? [['joint' => 'left_elbow', 'target' => 20, 'limit' => 35, 'beyond_by' => 15, 'limit_source' => 'estimated']] : []],
                    array_slice($ids, 0, $sent['top_k']), array_keys(array_slice($ids, 0, $sent['top_k'])),
                )]);
            },
        ]);
    }

    private function run_job(Analysis $analysis): Analysis
    {
        app()->call([new ProcessFigureAnalysis($analysis->id), 'handle']);

        return $analysis->fresh();
    }

    public function test_seeder_loads_the_generated_catalog_and_unpublishes_unusable_poses(): void
    {
        $catalog = json_decode(file_get_contents(config('figurepose.catalog_path')), true)['poses'];
        $published = array_filter($catalog, fn ($p) => $p['published']);

        $this->assertSame(count($catalog), PoseCatalog::count());
        $this->assertSame(count($published), PoseCatalog::published()->count());
        $pose = PoseCatalog::where('slug', 'rider-ready-stance')->firstOrFail();
        $this->assertArrayHasKey('left_elbow', $pose->joint_positions['keypoints']);
        $this->assertCount(2, $pose->joint_positions['image_size']);
        $this->assertNotEmpty($pose->instructions);
        $this->assertSame('Fuyoh!', $pose->reference_credit['creator']);
    }

    public function test_completed_analysis_gets_ranked_recommendations_from_its_figure_type(): void
    {
        $this->fakeAi($sent);

        $analysis = $this->run_job($this->analysis());

        $this->assertSame(AnalysisStatus::Completed, $analysis->status);
        $humanoid = PoseCatalog::published()->whereHas('profile', fn ($q) => $q->where('slug', 'humanoid_v1'))->pluck('id')->all();
        $this->assertEqualsCanonicalizing($humanoid, array_column($sent['candidates'], 'id'));
        $this->assertSame([900, 1200], $sent['pose']['image_size']);
        $this->assertSame(5, $sent['top_k']);

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$analysis->public_id}")
            ->assertOk()
            ->assertJsonCount(5, 'data.recommendations')
            ->assertJsonPath('data.recommendations.0.rank', 1)
            ->assertJsonPath('data.recommendations.0.mirrored', true)
            ->assertJsonPath('data.recommendations.0.warnings.0.joint', 'left_elbow')
            ->assertJsonPath('data.recommendations.0.pose.source', 'catalog')
            ->assertJsonPath('data.recommendations.1.mirrored', false);
    }

    public function test_the_figures_own_joint_limits_are_sent(): void
    {
        $this->fakeAi($sent);
        $user = User::factory()->create();
        $figure = $user->figures()->create(['name' => 'Stiff one', 'figure_profile_id' => 1,
            'articulation_config' => ['left_knee' => ['min' => 120, 'max' => 180]]]);

        $this->run_job($this->analysis(['user_id' => $user->id, 'guest_key_hash' => null, 'figure_id' => $figure->id]));

        // Sent as a JSON object, so "no limits" goes out as {} rather than [].
        $this->assertSame(['left_knee' => ['min' => 120, 'max' => 180]], json_decode(json_encode($sent['figure_limits']), true));
    }

    public function test_ranking_failure_leaves_the_analysis_for_a_retry(): void
    {
        Http::fake([
            '*/v1/analyze' => Http::response($this->analyzeResponse()),
            '*/v1/recommend' => Http::response('down', 500),
        ]);
        $analysis = $this->analysis();

        try {
            $this->run_job($analysis);
            $this->fail('Expected the job to throw so the queue retries it.');
        } catch (RequestException) {
        }

        $this->assertSame(AnalysisStatus::Processing, $analysis->fresh()->status);
        $this->assertSame(0, $analysis->recommendations()->count());
    }

    public function test_rerunning_with_another_type_replaces_the_recommendations(): void
    {
        $this->fakeAi($sent);
        $analysis = $this->run_job($this->analysis());
        $before = $analysis->recommendations()->pluck('id')->all();

        $this->fakeAi($sent);
        $analysis->update(['status' => AnalysisStatus::Pending]);
        $analysis = $this->run_job($analysis);

        $after = $analysis->recommendations()->pluck('id')->all();
        $this->assertCount(5, $after);
        $this->assertEmpty(array_intersect($before, $after));
    }
}

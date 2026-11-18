<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Models\PoseCatalog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

/** Pose ideas: the character a figure shows (suggested or typed) and figures that look like it come first. */
class PoseIdeasTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    /** @var list<array<string, mixed>> */
    private array $inspireCalls = [];

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        Storage::fake('s3');
        Storage::disk('s3')->put('analyses/x/photo.jpg', 'photo-bytes');
        $this->guestKey = (string) Str::uuid();
        config(['figurepose.character.enabled' => true, 'figurepose.character.provider_name' => 'OpenAI']);
    }

    private function fakeAi(array $identify = [], int $identifyStatus = 200): void
    {
        $this->inspireCalls = [];
        Http::fake([
            '*/v1/analyze' => Http::response([
                'model_version' => 'test', 'stage' => 'keypoints', 'profile' => 'humanoid_v1',
                'quality' => ['ok' => true, 'issues' => []],
                'figures' => [['bbox' => [0.2, 0.1, 0.8, 0.95], 'score' => 0.7]], 'selected_figure' => 0,
                'classification' => ['profile' => 'humanoid_v1', 'confidence' => 0.9, 'scores' => [], 'needs_confirmation' => false, 'source' => 'model'],
                'pose' => ['profile' => 'humanoid_v1', 'visible_count' => 16, 'hidden' => [],
                    'keypoints' => ['neck' => ['x' => 0.5, 'y' => 0.2, 'confidence' => 0.9, 'visibility' => 'visible']]],
                'appearance' => ['embedding' => [0.6, 0.8], 'version' => 'siglip-test'],
            ]),
            '*/v1/inspire' => function ($request) {
                $this->inspireCalls[] = $sent = $request->data();
                // Same character first, then the rest, like the AI service.
                $same = array_values(array_filter($sent['candidates'], fn ($c) => $sent['character'] && $c['character'] === 'Superman'));
                $rest = array_values(array_filter($sent['candidates'], fn ($c) => ! in_array($c, $same, true)));

                return Http::response(['matcher_version' => 'inspire-0.1', 'profile' => $sent['profile'], 'basis' => 'pose', 'remaining' => 0,
                    'results' => array_map(fn ($c) => [
                        'id' => $c['id'], 'score' => 0.8, 'similarity' => 0.6, 'feasibility' => 1.0, 'components' => [], 'shared_joints' => 12,
                        'mirrored' => false, 'warnings' => [], 'changes' => [],
                        'reasons' => in_array($c, $same, true) ? ['same_character', 'new_pose'] : ['similar_look'],
                        'group' => in_array($c, $same, true) ? 'same_character' : 'similar_look', 'look' => 0.71,
                    ], array_slice([...$same, ...$rest], 0, $sent['top_k']))]);
            },
            '*/v1/identify' => Http::response($identify + [
                'provider' => 'openai', 'character' => 'Superman', 'variant' => '', 'franchise' => 'Marvel',
                'figure_line' => '', 'confidence' => 'high', 'display_name' => 'Superman', 'key' => 'superman', 'model' => 'gpt-5.4',
            ], $identifyStatus),
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

    private function api(): self
    {
        return $this->withHeader('X-Guest-Key', $this->guestKey);
    }

    public function test_the_catalog_carries_characters_and_looks(): void
    {
        $pose = PoseCatalog::where('slug', 'stop-hand')->firstOrFail();
        $this->assertSame('Superman', $pose->character_name);
        $this->assertCount(768, $pose->appearance['embedding']);
    }

    public function test_ideas_are_ranked_by_look_and_shown_in_groups(): void
    {
        $this->fakeAi();
        $analysis = $this->analyzed();

        $sent = $this->inspireCalls[0];
        $this->assertSame([0.6, 0.8], $sent['appearance']);
        $this->assertNull($sent['character']);
        $this->assertSame(8, $sent['top_k']);
        $this->assertContains('Superman', array_column($sent['candidates'], 'character'));
        $this->assertCount(768, $sent['candidates'][0]['appearance']);

        $this->api()->getJson("/api/v1/analyses/{$analysis->public_id}")
            ->assertJsonPath('data.recommendations.0.group', 'similar_look')
            ->assertJsonPath('data.recommendations.0.look', 0.71)
            ->assertJsonPath('data.character.name', null)
            ->assertJsonPath('data.character_recognition', ['available' => true, 'provider' => 'OpenAI']);
    }

    public function test_recognizing_the_character_needs_consent_then_puts_that_character_first(): void
    {
        $this->fakeAi();
        $analysis = $this->analyzed();

        $this->api()->postJson("/api/v1/analyses/{$analysis->public_id}/character/recognize")
            ->assertStatus(422)->assertJsonValidationErrors('consent');
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/v1/identify'));

        $this->api()->postJson("/api/v1/analyses/{$analysis->public_id}/character/recognize", ['consent' => true])
            ->assertOk()
            ->assertJsonPath('message', 'Looks like Superman. Not right? Change it.')
            ->assertJsonPath('data.character', ['name' => 'Superman', 'source' => 'ai', 'franchise' => 'Marvel', 'confidence' => 'high'])
            ->assertJsonPath('data.recommendations.0.group', 'same_character')
            ->assertJsonPath('data.recommendations.0.pose.slug', 'stop-hand');

        Http::assertSent(fn ($r) => str_contains($r->url(), '/v1/identify') && str_contains($r->body(), '[0.2,0.1,0.8,0.95]'));
        $this->assertSame('Superman', end($this->inspireCalls)['character']);
    }

    public function test_an_unsure_answer_is_not_used(): void
    {
        $this->fakeAi(['character' => '', 'display_name' => '', 'confidence' => 'low']);
        $analysis = $this->analyzed();
        $this->api()->postJson("/api/v1/analyses/{$analysis->public_id}/character/recognize", ['consent' => true])
            ->assertOk()
            ->assertJsonPath('message', "We couldn't tell who this is. Type the name to see that character's poses.")
            ->assertJsonPath('data.character.name', null);
    }

    public function test_a_declined_photo_is_explained(): void
    {
        $this->fakeAi(['detail' => 'OpenAI declined'], 422);
        $analysis = $this->analyzed();
        $this->api()->postJson("/api/v1/analyses/{$analysis->public_id}/character/recognize", ['consent' => true])
            ->assertStatus(422)->assertJsonPath('message', 'The recognition service declined this photo. Type the name instead.');
    }

    public function test_the_user_can_type_correct_or_clear_the_character(): void
    {
        $this->fakeAi();
        $analysis = $this->analyzed();

        $this->api()->putJson("/api/v1/analyses/{$analysis->public_id}/character", ['name' => '  Superman '])
            ->assertOk()
            ->assertJsonPath('data.character.name', 'Superman')
            ->assertJsonPath('data.character.source', 'user')
            ->assertJsonPath('data.recommendations.0.group', 'same_character');

        $this->api()->putJson("/api/v1/analyses/{$analysis->public_id}/character", ['name' => null])
            ->assertOk()->assertJsonPath('data.character.name', null)->assertJsonPath('data.recommendations.0.group', 'similar_look');

        $this->withHeader('X-Guest-Key', (string) Str::uuid())
            ->putJson("/api/v1/analyses/{$analysis->public_id}/character", ['name' => 'x'])->assertNotFound();
    }

    public function test_recognition_can_be_switched_off(): void
    {
        $this->fakeAi();
        $analysis = $this->analyzed();
        config(['figurepose.character.enabled' => false]);

        $this->api()->postJson("/api/v1/analyses/{$analysis->public_id}/character/recognize", ['consent' => true])->assertStatus(503);
        $this->api()->getJson("/api/v1/analyses/{$analysis->public_id}")->assertJsonPath('data.character_recognition.available', false);
    }
}

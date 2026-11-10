<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Models\FigureProfile;
use Database\Seeders\FigureProfileSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class AnalysisPoseResultTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed(FigureProfileSeeder::class);
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
            'image_disk' => 's3',
            'image_path' => 'analyses/x/photo.jpg',
            'image_mime' => 'image/jpeg',
            'image_size' => 5,
            'image_width' => 900,
            'image_height' => 1200,
        ]);
    }

    private function aiResponse(string $profile = 'mecha_v1', bool $confirm = false): array
    {
        return [
            'model_version' => 'pipeline-0.2+test',
            'stage' => 'keypoints',
            'profile' => $profile,
            'quality' => ['ok' => true, 'issues' => []],
            'figures' => [['bbox' => [0.2, 0.1, 0.8, 0.95], 'score' => 0.71]],
            'selected_figure' => 0,
            'classification' => ['profile' => $profile, 'confidence' => $confirm ? 0.45 : 0.9,
                'scores' => [$profile => 0.9], 'needs_confirmation' => $confirm, 'source' => 'model'],
            'pose' => ['profile' => $profile, 'visible_count' => 14, 'hidden' => ['left_wrist'],
                'keypoints' => ['head' => ['x' => 0.5, 'y' => 0.1, 'confidence' => 0.9, 'visibility' => 'visible', 'source' => 'derived']],
                'joint_angles' => ['left_knee' => 172.5], 'orientation' => 'front', 'embedding' => [0.1], 'embedding_version' => 'geo-v1'],
            'models' => ['detector' => 'owlv2'],
            'timings_ms' => ['detect' => 900],
        ];
    }

    private function runJob(Analysis $analysis): Analysis
    {
        app()->call([new ProcessFigureAnalysis($analysis->id), 'handle']);

        return $analysis->fresh();
    }

    public function test_completed_analysis_returns_figures_type_and_pose(): void
    {
        Http::fake(['*/v1/analyze' => Http::response($this->aiResponse('mecha_v1'))]);
        $analysis = $this->runJob($this->analysis());

        $this->assertSame(AnalysisStatus::Completed, $analysis->status);
        $this->assertSame('mecha_v1', $analysis->profile->slug);

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$analysis->public_id}")
            ->assertOk()
            ->assertJsonPath('data.profile', 'mecha_v1')
            ->assertJsonPath('data.figures.0.score', 0.71)
            ->assertJsonPath('data.selected_figure', 0)
            ->assertJsonPath('data.classification.needs_confirmation', false)
            ->assertJsonPath('data.pose.visible_count', 14)
            ->assertJsonPath('data.pose.joint_angles.left_knee', 172.5);
    }

    public function test_automatic_mode_lets_the_ai_classify_and_manual_mode_sends_the_type(): void
    {
        Http::fake(['*/v1/analyze' => Http::response($this->aiResponse())]);
        $mecha = FigureProfile::where('slug', 'mecha_v1')->firstOrFail();

        $this->runJob($this->analysis());
        Http::assertSent(fn ($req) => ! str_contains($req->body(), 'name="profile"'));

        $this->runJob($this->analysis(['analysis_mode' => AnalysisMode::Manual, 'figure_profile_id' => $mecha->id]));
        Http::assertSent(fn ($req) => str_contains($req->body(), 'name="profile"') && str_contains($req->body(), 'mecha_v1'));
    }

    public function test_photo_without_a_figure_fails_with_no_figure(): void
    {
        Http::fake(['*/v1/analyze' => Http::response([
            'model_version' => 'pipeline-0.2+test', 'stage' => 'detected', 'figures' => [],
            'quality' => ['ok' => false, 'issues' => [['code' => 'no_figure', 'message' => "We couldn't find a figure in this photo."]]],
        ])]);

        $analysis = $this->runJob($this->analysis());

        $this->assertSame(AnalysisStatus::Failed, $analysis->status);
        $this->assertSame('no_figure', $analysis->failure_code);
    }

    public function test_user_can_confirm_another_type_and_the_photo_is_analyzed_again(): void
    {
        Http::fake(['*/v1/analyze' => Http::response($this->aiResponse('humanoid_v1', confirm: true))]);
        $analysis = $this->runJob($this->analysis());
        $anime = FigureProfile::where('slug', 'anime_v1')->firstOrFail();

        Queue::fake();
        $this->withHeader('X-Guest-Key', $this->guestKey)
            ->postJson("/api/v1/analyses/{$analysis->public_id}/profile", ['figure_profile_id' => $anime->id])
            ->assertStatus(202)
            ->assertJsonPath('data.status', 'pending');

        $fresh = $analysis->fresh();
        $this->assertSame(AnalysisMode::Manual, $fresh->analysis_mode);
        $this->assertSame('anime_v1', $fresh->profile->slug);
        $this->assertNull($fresh->pose_data);
        Queue::assertPushed(ProcessFigureAnalysis::class, fn ($job) => $job->analysisId === $analysis->id);
    }

    public function test_confirming_needs_ownership_a_valid_type_and_a_finished_analysis(): void
    {
        $analysis = $this->analysis();
        $anime = FigureProfile::where('slug', 'anime_v1')->firstOrFail();
        $url = "/api/v1/analyses/{$analysis->public_id}/profile";

        $this->withHeader('X-Guest-Key', (string) Str::uuid())->postJson($url, ['figure_profile_id' => $anime->id])->assertNotFound();
        $this->withHeader('X-Guest-Key', $this->guestKey)->postJson($url, ['figure_profile_id' => 999])->assertStatus(422);
        $this->withHeader('X-Guest-Key', $this->guestKey)->postJson($url, ['figure_profile_id' => $anime->id])->assertStatus(409);
    }
}

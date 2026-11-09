<?php

namespace Tests\Feature;

use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Models\FigureProfile;
use App\Models\User;
use Database\Seeders\FigureProfileSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class AnalysisUploadTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
        Queue::fake();
        $this->seed(FigureProfileSeeder::class);
        $this->guestKey = (string) Str::uuid();
    }

    private function upload(array $overrides = [], ?string $guestKey = null)
    {
        return $this->withHeader('X-Guest-Key', $guestKey ?? $this->guestKey)->postJson('/api/v1/analyses', array_merge([
            'image' => UploadedFile::fake()->image('figure.jpg', 900, 1200),
            'analysis_mode' => 'automatic',
        ], $overrides));
    }

    public function test_guest_can_upload_a_photo_and_analysis_is_queued(): void
    {
        $response = $this->upload();

        $response->assertStatus(202)
            ->assertJsonPath('success', true)
            ->assertJsonPath('data.status', 'pending');

        $analysis = Analysis::firstOrFail();
        $this->assertSame($response->json('data.analysis_id'), $analysis->public_id);
        $this->assertNull($analysis->user_id);
        $this->assertSame(900, $analysis->image_width);
        $this->assertStringContainsString($analysis->public_id, $analysis->image_path);
        Storage::disk('s3')->assertExists($analysis->image_path);
        Queue::assertPushed(ProcessFigureAnalysis::class, fn ($job) => $job->analysisId === $analysis->id);
    }

    public function test_signed_in_user_owns_their_analysis(): void
    {
        $user = User::factory()->create();
        Sanctum::actingAs($user);

        $this->postJson('/api/v1/analyses', [
            'image' => UploadedFile::fake()->image('figure.png', 800, 800),
            'analysis_mode' => 'automatic',
        ])->assertStatus(202);

        $this->assertSame($user->id, Analysis::firstOrFail()->user_id);
    }

    public function test_upload_without_identity_is_rejected(): void
    {
        $this->postJson('/api/v1/analyses', [
            'image' => UploadedFile::fake()->image('figure.jpg', 900, 1200),
            'analysis_mode' => 'automatic',
        ])->assertStatus(401);

        Queue::assertNothingPushed();
    }

    public function test_unsupported_format_is_rejected(): void
    {
        $this->upload(['image' => UploadedFile::fake()->create('figure.gif', 200, 'image/gif')])
            ->assertStatus(422)->assertJsonValidationErrors('image');
    }

    public function test_too_small_photo_is_rejected(): void
    {
        $this->upload(['image' => UploadedFile::fake()->image('tiny.jpg', 200, 200)])
            ->assertStatus(422)->assertJsonValidationErrors('image');
    }

    public function test_manual_mode_requires_a_profile(): void
    {
        $this->upload(['analysis_mode' => 'manual'])
            ->assertStatus(422)->assertJsonValidationErrors('figure_profile_id');

        $profile = FigureProfile::where('slug', 'mecha_v1')->firstOrFail();
        $this->upload(['analysis_mode' => 'manual', 'figure_profile_id' => $profile->id])->assertStatus(202);
    }

    public function test_owner_can_poll_status_but_others_get_404(): void
    {
        $id = $this->upload()->json('data.analysis_id');

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$id}")
            ->assertOk()
            ->assertJsonPath('data.status', AnalysisStatus::Pending->value)
            ->assertJsonPath('data.poll_after_seconds', 2);

        $this->withHeader('X-Guest-Key', (string) Str::uuid())->getJson("/api/v1/analyses/{$id}")->assertNotFound();

        $this->flushHeaders();
        Sanctum::actingAs(User::factory()->create());
        $this->getJson("/api/v1/analyses/{$id}")->assertNotFound();
    }
}

<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Models\Analysis;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class AnalysisHistoryTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
    }

    private function analysis(array $owner): Analysis
    {
        $path = 'analyses/2026/11/'.Str::uuid().'.jpg';
        Storage::disk('s3')->put($path, 'photo-bytes');

        return Analysis::create($owner + [
            'analysis_mode' => AnalysisMode::Automatic,
            'status' => AnalysisStatus::Completed,
            'image_disk' => 's3',
            'image_path' => $path,
            'image_mime' => 'image/jpeg',
            'image_size' => 11,
            'image_width' => 900,
            'image_height' => 1200,
        ]);
    }

    public function test_history_needs_an_account_or_a_guest_key(): void
    {
        $this->getJson('/api/v1/analyses')->assertUnauthorized();
    }

    public function test_user_sees_only_their_own_analyses_newest_first(): void
    {
        $me = User::factory()->create();
        $older = $this->analysis(['user_id' => $me->id]);
        $newer = $this->analysis(['user_id' => $me->id]);
        $this->analysis(['user_id' => User::factory()->create()->id]);
        $this->analysis(['guest_key_hash' => Analysis::hashGuestKey((string) Str::uuid())]);

        Sanctum::actingAs($me);

        $this->getJson('/api/v1/analyses')
            ->assertOk()
            ->assertJsonPath('meta.total', 2)
            ->assertJsonPath('data.0.analysis_id', $newer->public_id)
            ->assertJsonPath('data.1.analysis_id', $older->public_id);
    }

    public function test_guest_sees_only_analyses_from_their_device(): void
    {
        $key = (string) Str::uuid();
        $mine = $this->analysis(['guest_key_hash' => Analysis::hashGuestKey($key)]);
        $this->analysis(['guest_key_hash' => Analysis::hashGuestKey((string) Str::uuid())]);

        $this->withHeader('X-Guest-Key', $key)->getJson('/api/v1/analyses')
            ->assertOk()
            ->assertJsonPath('meta.total', 1)
            ->assertJsonPath('data.0.analysis_id', $mine->public_id);
    }

    public function test_owner_can_delete_an_analysis_and_its_photo(): void
    {
        $me = User::factory()->create();
        $analysis = $this->analysis(['user_id' => $me->id]);
        Sanctum::actingAs($me);

        $this->deleteJson("/api/v1/analyses/{$analysis->public_id}")->assertOk();

        $this->assertDatabaseMissing('analyses', ['id' => $analysis->id]);
        Storage::disk('s3')->assertMissing($analysis->image_path);
    }

    public function test_nobody_else_can_delete_an_analysis(): void
    {
        $analysis = $this->analysis(['user_id' => User::factory()->create()->id]);

        $this->withHeader('X-Guest-Key', (string) Str::uuid())
            ->deleteJson("/api/v1/analyses/{$analysis->public_id}")->assertNotFound();

        $this->flushHeaders();
        Sanctum::actingAs(User::factory()->create());
        $this->deleteJson("/api/v1/analyses/{$analysis->public_id}")->assertNotFound();

        $this->assertDatabaseHas('analyses', ['id' => $analysis->id]);
        Storage::disk('s3')->assertExists($analysis->image_path);
    }
}

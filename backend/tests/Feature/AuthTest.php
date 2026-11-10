<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Models\Analysis;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Tests\TestCase;

class AuthTest extends TestCase
{
    use RefreshDatabase;

    private function register(array $overrides = [], array $headers = [])
    {
        return $this->withHeaders($headers)->postJson('/api/v1/auth/register', array_merge([
            'name' => 'Rina Collector',
            'email' => 'Rina@Example.com',
            'password' => 'figure-shelf-42',
        ], $overrides));
    }

    public function test_register_creates_an_account_and_returns_a_token(): void
    {
        $response = $this->register();

        $response->assertCreated()
            ->assertJsonPath('data.user.email', 'rina@example.com')
            ->assertJsonPath('data.token_type', 'Bearer')
            ->assertJsonMissingPath('data.user.password');

        $this->assertNotEmpty($response->json('data.token'));
        $this->assertNotSame('figure-shelf-42', User::firstOrFail()->password);
    }

    public function test_register_rejects_a_duplicate_email_and_a_short_password(): void
    {
        User::factory()->create(['email' => 'rina@example.com']);

        $this->register()->assertStatus(422)->assertJsonValidationErrors('email');
        $this->register(['email' => 'new@example.com', 'password' => 'short'])
            ->assertStatus(422)->assertJsonValidationErrors('password');
    }

    public function test_login_returns_a_token_that_works(): void
    {
        $user = User::factory()->create(['email' => 'rina@example.com', 'password' => 'figure-shelf-42']);

        $token = $this->postJson('/api/v1/auth/login', ['email' => 'rina@example.com', 'password' => 'figure-shelf-42'])
            ->assertOk()->json('data.token');

        $this->withToken($token)->getJson('/api/v1/auth/me')
            ->assertOk()->assertJsonPath('data.id', $user->id);
    }

    public function test_login_gives_the_same_error_for_wrong_password_and_unknown_email(): void
    {
        User::factory()->create(['email' => 'rina@example.com', 'password' => 'figure-shelf-42']);

        $wrongPassword = $this->postJson('/api/v1/auth/login', ['email' => 'rina@example.com', 'password' => 'nope-nope-nope']);
        $unknownEmail = $this->postJson('/api/v1/auth/login', ['email' => 'ghost@example.com', 'password' => 'figure-shelf-42']);

        $wrongPassword->assertStatus(422);
        $unknownEmail->assertStatus(422);
        $this->assertSame($wrongPassword->json('errors'), $unknownEmail->json('errors'));
    }

    public function test_login_is_rate_limited(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/api/v1/auth/login', ['email' => 'rina@example.com', 'password' => 'wrong-password'])->assertStatus(422);
        }

        $this->postJson('/api/v1/auth/login', ['email' => 'rina@example.com', 'password' => 'wrong-password'])->assertStatus(429);
    }

    public function test_logout_revokes_the_token(): void
    {
        $token = $this->register()->json('data.token');

        $this->withToken($token)->postJson('/api/v1/auth/logout')->assertOk();

        $this->assertDatabaseCount('personal_access_tokens', 0);
    }

    public function test_me_requires_a_token(): void
    {
        $this->getJson('/api/v1/auth/me')->assertUnauthorized();
    }

    public function test_signing_up_keeps_analyses_made_as_a_guest(): void
    {
        $guestKey = (string) Str::uuid();
        $mine = $this->guestAnalysis($guestKey);
        $someoneElses = $this->guestAnalysis((string) Str::uuid());

        $response = $this->register([], ['X-Guest-Key' => $guestKey]);

        $response->assertCreated()->assertJsonPath('data.claimed_analyses', 1);
        $this->assertSame($response->json('data.user.id'), $mine->fresh()->user_id);
        $this->assertNull($mine->fresh()->guest_key_hash);
        $this->assertNull($someoneElses->fresh()->user_id);
    }

    private function guestAnalysis(string $guestKey): Analysis
    {
        return Analysis::create([
            'guest_key_hash' => Analysis::hashGuestKey($guestKey),
            'analysis_mode' => AnalysisMode::Automatic,
            'status' => AnalysisStatus::Completed,
            'image_disk' => 's3',
            'image_path' => 'analyses/x/'.Str::random(8).'.jpg',
            'image_mime' => 'image/jpeg',
            'image_size' => 10,
            'image_width' => 900,
            'image_height' => 1200,
        ]);
    }
}

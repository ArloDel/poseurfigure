<?php

namespace Tests\Feature;

use App\Models\Figure;
use App\Models\FigureProfile;
use App\Models\User;
use Database\Seeders\FigureProfileSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class FigureApiTest extends TestCase
{
    use RefreshDatabase;

    private FigureProfile $mecha;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed(FigureProfileSeeder::class);
        $this->mecha = FigureProfile::where('slug', 'mecha_v1')->firstOrFail();
    }

    public function test_figures_require_an_account(): void
    {
        $this->getJson('/api/v1/figures')->assertUnauthorized();
        $this->postJson('/api/v1/figures', [])->assertUnauthorized();
    }

    public function test_user_can_add_a_figure_with_known_joint_limits(): void
    {
        Sanctum::actingAs($user = User::factory()->create());

        $this->postJson('/api/v1/figures', [
            'name' => 'RX-78-2',
            'brand' => 'Bandai',
            'figure_profile_id' => $this->mecha->id,
            'articulation_config' => ['left_elbow' => ['min' => 40, 'max' => 180]],
        ])
            ->assertCreated()
            ->assertJsonPath('data.name', 'RX-78-2')
            ->assertJsonPath('data.profile', 'mecha_v1')
            ->assertJsonPath('data.articulation_config.left_elbow.min', 40);

        $this->assertSame($user->id, Figure::firstOrFail()->user_id);
    }

    public function test_figure_needs_a_name_and_a_supported_type(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $this->postJson('/api/v1/figures', ['figure_profile_id' => 9999])
            ->assertStatus(422)->assertJsonValidationErrors(['name', 'figure_profile_id']);

        $this->postJson('/api/v1/figures', [
            'name' => 'Odd one', 'figure_profile_id' => $this->mecha->id,
            'articulation_config' => ['left_elbow' => ['min' => 40]],
        ])->assertStatus(422)->assertJsonValidationErrors('articulation_config.left_elbow.max');
    }

    public function test_user_only_sees_their_own_figures(): void
    {
        $me = User::factory()->create();
        $other = User::factory()->create();
        $me->figures()->create(['name' => 'Mine', 'figure_profile_id' => $this->mecha->id]);
        $other->figures()->create(['name' => 'Theirs', 'figure_profile_id' => $this->mecha->id]);

        Sanctum::actingAs($me);

        $this->getJson('/api/v1/figures')
            ->assertOk()->assertJsonCount(1, 'data')->assertJsonPath('data.0.name', 'Mine');
    }
}

<?php

namespace Tests\Feature;

use App\Models\Favorite;
use App\Models\PoseCatalog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class FavoriteApiTest extends TestCase
{
    use RefreshDatabase;

    private PoseCatalog $pose;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        $this->pose = PoseCatalog::where('slug', 'rider-ready-stance')->firstOrFail();
    }

    public function test_favorites_require_an_account(): void
    {
        $this->getJson('/api/v1/favorites')->assertUnauthorized();
        $this->postJson('/api/v1/favorites', ['pose_id' => $this->pose->id])->assertUnauthorized();
        $this->deleteJson('/api/v1/favorites/1')->assertUnauthorized();
    }

    public function test_user_can_save_list_and_remove_a_favorite(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $id = $this->postJson('/api/v1/favorites', ['pose_id' => $this->pose->id])
            ->assertCreated()
            ->assertJsonPath('data.pose.slug', 'rider-ready-stance')
            ->json('data.id');

        $this->getJson('/api/v1/favorites')
            ->assertOk()->assertJsonCount(1, 'data')->assertJsonPath('data.0.pose.source', 'catalog');

        $this->deleteJson("/api/v1/favorites/{$id}")->assertOk();
        $this->getJson('/api/v1/favorites')->assertOk()->assertJsonCount(0, 'data');
    }

    public function test_saving_the_same_pose_twice_keeps_one_favorite(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $first = $this->postJson('/api/v1/favorites', ['pose_id' => $this->pose->id])->assertCreated();
        $second = $this->postJson('/api/v1/favorites', ['pose_id' => $this->pose->id])->assertOk();

        $this->assertSame($first->json('data.id'), $second->json('data.id'));
        $this->assertSame(1, Favorite::count());
    }

    public function test_unknown_or_unpublished_pose_cannot_be_saved(): void
    {
        Sanctum::actingAs(User::factory()->create());
        $this->pose->update(['is_published' => false]);

        $this->postJson('/api/v1/favorites', ['pose_id' => 99999])->assertStatus(422)->assertJsonValidationErrors('pose_id');
        $this->postJson('/api/v1/favorites', ['pose_id' => $this->pose->id])->assertStatus(422);
    }

    public function test_user_cannot_see_or_remove_someone_elses_favorite(): void
    {
        $theirs = User::factory()->create()->favorites()->create(['pose_catalog_id' => $this->pose->id]);

        Sanctum::actingAs(User::factory()->create());

        $this->getJson('/api/v1/favorites')->assertOk()->assertJsonCount(0, 'data');
        $this->deleteJson("/api/v1/favorites/{$theirs->id}")->assertNotFound();
        $this->assertDatabaseHas('favorites', ['id' => $theirs->id]);
    }
}

<?php

namespace Tests\Feature;

use App\Models\PoseCatalog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CatalogApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
    }

    public function test_lists_the_three_mvp_profiles(): void
    {
        $this->getJson('/api/v1/figures/profiles')
            ->assertOk()
            ->assertJsonCount(3, 'data')
            ->assertJsonFragment(['slug' => 'humanoid_v1'])
            ->assertJsonFragment(['slug' => 'anime_v1'])
            ->assertJsonFragment(['slug' => 'mecha_v1']);
    }

    public function test_browses_and_filters_the_pose_catalog(): void
    {
        $this->getJson('/api/v1/poses')->assertOk()->assertJsonPath('meta.total', PoseCatalog::count());

        $mecha = $this->getJson('/api/v1/poses?profile=mecha_v1')->assertOk()->json('data');
        $this->assertNotEmpty($mecha);
        $this->assertSame(['mecha_v1'], array_values(array_unique(array_column($mecha, 'profile'))));
    }

    public function test_pose_detail_includes_structured_instructions(): void
    {
        $pose = PoseCatalog::where('slug', 'rider-ready-stance')->firstOrFail();

        $this->getJson("/api/v1/poses/{$pose->id}")
            ->assertOk()
            ->assertJsonPath('data.source', 'catalog')
            ->assertJsonPath('data.image_url', url('catalog/rider-ready-stance.jpg'))
            ->assertJsonPath('data.image_credit.license', 'CC BY 2.0')
            ->assertJsonStructure(['data' => ['instructions' => [['step', 'body_part', 'movement', 'target_angle', 'priority']]]]);
    }
}

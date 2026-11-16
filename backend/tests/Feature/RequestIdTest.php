<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class RequestIdTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Http::fake(['*/health' => Http::response(['status' => 'ok'])]);
    }

    public function test_a_request_id_from_the_proxy_is_kept_and_returned(): void
    {
        $this->withHeader('X-Request-Id', 'f7149cd911f7934845e0837cdc40960f')->getJson('/api/v1/poses')
            ->assertOk()
            ->assertHeader('X-Request-Id', 'f7149cd911f7934845e0837cdc40960f');
    }

    public function test_without_one_or_with_an_unsafe_one_a_new_id_is_made(): void
    {
        $id = $this->getJson('/api/v1/poses')->headers->get('X-Request-Id');
        $this->assertMatchesRegularExpression('/^[0-9a-f-]{36}$/', $id);

        $unsafe = $this->withHeader('X-Request-Id', "evil\nline")->getJson('/api/v1/poses')->headers->get('X-Request-Id');
        $this->assertNotSame("evil\nline", $unsafe);
        $this->assertMatchesRegularExpression('/^[0-9a-f-]{36}$/', $unsafe);
    }
}

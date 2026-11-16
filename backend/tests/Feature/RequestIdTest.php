<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Log\Events\MessageLogged;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Route;
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

    public function test_log_lines_written_during_the_request_carry_its_id(): void
    {
        Route::middleware('api')->get('/api/test-log', function () {
            Log::warning('something happened');

            return response()->json(['ok' => true]);
        });
        $seen = [];
        Log::listen(function (MessageLogged $e) use (&$seen) {
            $seen[] = $e->context;
        });

        $this->withHeader('X-Request-Id', 'trace-me-12345')->getJson('/api/test-log')->assertOk();

        $this->assertSame('trace-me-12345', $seen[0]['request_id'] ?? null);
    }
}

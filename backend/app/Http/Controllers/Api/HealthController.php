<?php

namespace App\Http\Controllers\Api;

use App\Services\AIService;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Throwable;

class HealthController extends ApiController
{
    /** Readiness of the API and the services it depends on. */
    public function __invoke(AIService $ai): JsonResponse
    {
        $checks = [
            'database' => $this->check(fn () => DB::select('select 1')),
            'ai_service' => $this->check(fn () => $ai->health()),
        ];
        $healthy = ! in_array(false, $checks, true);

        return response()->json([
            'success' => $healthy,
            'data' => ['status' => $healthy ? 'ok' : 'degraded', 'checks' => $checks],
        ], $healthy ? 200 : 503);
    }

    private function check(callable $probe): bool
    {
        try {
            $probe();

            return true;
        } catch (Throwable) {
            return false;
        }
    }
}

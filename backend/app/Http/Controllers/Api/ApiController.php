<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\JsonResource;

abstract class ApiController extends Controller
{
    /** Envelope from PRD 11: { success, message?, data }. */
    protected function ok(mixed $data, ?string $message = null, int $status = 200): JsonResponse
    {
        if ($data instanceof JsonResource) {
            $data = $data->resolve(request());
        }

        return response()->json(array_filter([
            'success' => true,
            'message' => $message,
            'data' => $data,
        ], fn ($v) => $v !== null), $status);
    }
}

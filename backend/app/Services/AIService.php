<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

/** Thin client for the Python FastAPI service. */
class AIService
{
    private function client(): PendingRequest
    {
        return Http::baseUrl(config('figurepose.ai_service.url'))
            ->timeout(config('figurepose.ai_service.timeout'))
            ->acceptJson();
    }

    /** @return array<string, mixed> */
    public function health(): array
    {
        return $this->client()->timeout(3)->get('/health')->throw()->json();
    }

    /**
     * Sends the photo for analysis. Sprint 1: image quality checks only; detection and keypoints come later.
     *
     * @return array{model_version: string, stage: string, quality: array<string, mixed>, pose: array<string, mixed>|null}
     */
    public function analyze(string $imageBytes, string $filename, ?string $profileSlug, string $requestId): array
    {
        return $this->client()
            ->withHeaders(['X-Request-Id' => $requestId])
            ->attach('image', $imageBytes, $filename)
            ->post('/v1/analyze', array_filter(['profile' => $profileSlug]))
            ->throw()
            ->json();
    }
}

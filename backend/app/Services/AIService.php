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
     * Ranks catalog poses for an analyzed pose (PRD 8.4). Geometry only, so it answers in milliseconds.
     *
     * @param  array<string, array>  $keypoints  the analysis' pose keypoints
     * @param  array{0: int, 1: int}  $imageSize
     * @param  list<array{id: int, keypoints: array, image_size: array}>  $candidates
     * @param  array<string, array{min: float, max: float}>  $figureLimits
     * @return array{matcher_version: string, results: list<array>}
     */
    public function recommend(string $profile, array $keypoints, array $imageSize, array $candidates, array $figureLimits, int $topK, string $requestId, array $excludeIds = []): array
    {
        return $this->client()
            ->withHeaders(['X-Request-Id' => $requestId])
            ->post('/v1/recommend', [
                'profile' => $profile,
                'pose' => ['keypoints' => $keypoints, 'image_size' => $imageSize],
                'candidates' => $candidates,
                'figure_limits' => (object) $figureLimits,
                'top_k' => $topK,
                'exclude_ids' => array_values($excludeIds),
            ])
            ->throw()
            ->json();
    }

    /**
     * Asks for an AI visual of the photo's figure in a target pose (PRD 8.6). The response carries the image
     * (base64) and its validation against the target pose.
     *
     * @param  array<string, mixed>  $payload  profile, target {keypoints, image_size}, instructions, mirrored
     * @return array{provider: string, image_base64: string, mime: string, validation: array<string, mixed>, prompt: string}
     */
    public function generate(string $imageBytes, string $filename, array $payload, string $requestId): array
    {
        return $this->client()
            ->withHeaders(['X-Request-Id' => $requestId])
            ->attach('image', $imageBytes, $filename)
            ->post('/v1/generate', ['payload' => json_encode($payload)])
            ->throw()
            ->json();
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

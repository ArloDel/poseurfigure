<?php

namespace App\Jobs;

use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use App\Models\GeneratedImage;
use App\Services\AIService;
use App\Services\StorageService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Throwable;

class GeneratePoseImage implements ShouldQueue
{
    use Queueable;

    // Above the AI request timeout (figurepose.generation.request_timeout, 110 s) and below the queue's
    // retry_after (REDIS_QUEUE_RETRY_AFTER, 150 s in compose), or a slow job would start twice and be billed twice.
    public int $timeout = 120;

    // One retry only: every attempt may be billed by the image provider.
    public int $tries = 2;

    public function __construct(public int $generatedImageId) {}

    /** @return list<int> */
    public function backoff(): array
    {
        return [10];
    }

    public function handle(AIService $ai, StorageService $storage): void
    {
        $image = GeneratedImage::with(['analysis.profile', 'pose'])->find($this->generatedImageId);
        if ($image === null || $image->generation_status !== GenerationStatus::Pending) {
            return;
        }
        $analysis = $image->analysis;
        $target = $image->pose->joint_positions;

        try {
            $result = $ai->generate(
                $storage->read($analysis->image_disk, $analysis->image_path),
                basename($analysis->image_path),
                [
                    'profile' => $analysis->profile->slug,
                    'target' => ['keypoints' => $target['keypoints'], 'image_size' => $target['image_size']],
                    'instructions' => $image->pose->instructions ?? [],
                    'mirrored' => $image->mirrored,
                ],
                $analysis->public_id,
                $this->referencePhoto($image->pose->reference_image),
            );
        } catch (RequestException $e) {
            // 422: the provider refused (moderation, bad input). Another paid try would get the same answer.
            if ($e->response->status() === 422) {
                $this->fail($e);

                return;
            }
            throw $e;
        }

        $bytes = base64_decode($result['image_base64'], true);
        if ($bytes === false || $bytes === '') {
            throw new \RuntimeException('The AI service returned an unreadable image.');
        }
        $stored = $storage->storeGenerated($bytes, (string) Str::uuid());

        $image->update([
            'image_disk' => $stored['disk'],
            'image_path' => $stored['path'],
            'provider' => $result['provider'] ?? null,
            'generation_status' => GenerationStatus::Generated,
            // generated -> validated | rejected (PRD 8.6). Anything else stays unvalidated.
            'validation_status' => ValidationStatus::tryFrom($result['validation']['status'] ?? '') ?? ValidationStatus::Unvalidated,
            'details' => ['validation' => $result['validation'] ?? null, 'prompt' => $result['prompt'] ?? null],
        ]);
    }

    /** The catalog photo of the target pose, from public/ (catalog/<slug>.jpg). Optional: the AI service also draws the pose. */
    private function referencePhoto(?string $path): ?string
    {
        if ($path === null || str_contains($path, '..')) {
            return null;
        }
        $file = public_path($path);

        return is_file($file) ? file_get_contents($file) : null;
    }

    public function failed(?Throwable $e): void
    {
        Log::warning('AI visual failed', ['generated_image_id' => $this->generatedImageId, 'error' => $e?->getMessage()]);

        // 422 from the AI service: the image service declined this photo (moderation). Trying again won't help;
        // in testing it was the user's photo itself (a figure aiming a pistol), not the catalog reference.
        $refused = $e instanceof RequestException && $e->response->status() === 422;

        GeneratedImage::whereKey($this->generatedImageId)->update([
            'generation_status' => GenerationStatus::Failed,
            'failure_message' => $refused
                ? "The image service declined this photo, so there's no AI visual for it. The steps above still work."
                : "We couldn't make this visual. Try again in a few minutes.",
        ]);
    }
}

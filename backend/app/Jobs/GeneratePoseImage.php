<?php

namespace App\Jobs;

use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use App\Models\GeneratedImage;
use App\Services\AIService;
use App\Services\StorageService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Throwable;

class GeneratePoseImage implements ShouldQueue
{
    use Queueable;

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
        );

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

    public function failed(?Throwable $e): void
    {
        Log::warning('AI visual failed', ['generated_image_id' => $this->generatedImageId, 'error' => $e?->getMessage()]);

        GeneratedImage::whereKey($this->generatedImageId)->update([
            'generation_status' => GenerationStatus::Failed,
            'failure_message' => "We couldn't make this visual. Try again in a few minutes.",
        ]);
    }
}

<?php

namespace App\Services;

use App\Enums\AnalysisStatus;
use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use App\Jobs\GeneratePoseImage;
use App\Models\Analysis;
use App\Models\GeneratedImage;
use App\Models\PoseCatalog;
use App\Support\Requester;
use Symfony\Component\HttpKernel\Exception\HttpException;

/** Optional AI visuals for a recommended pose (PRD 4.5 REC-08..10, 8.6). */
class GenerationService
{
    /**
     * Starts (or returns the existing) AI visual of an analysis' figure in a catalog pose.
     * The caller has already checked ownership and consent.
     */
    public function request(Analysis $analysis, PoseCatalog $pose, bool $mirrored, Requester $requester): GeneratedImage
    {
        if (! config('figurepose.generation.enabled')) {
            throw new HttpException(503, 'AI visuals are not available on this server.');
        }
        if ($analysis->status !== AnalysisStatus::Completed || empty($analysis->pose_data['pose'])) {
            throw new HttpException(409, 'AI visuals need a finished analysis.');
        }
        if (! $pose->is_published || $pose->figure_profile_id !== $analysis->figure_profile_id) {
            throw new HttpException(422, "That pose isn't for this figure type.");
        }

        // Same analysis + pose + mirroring = same image: a repeated tap or retry must not bill twice.
        $key = hash('sha256', "{$analysis->id}|{$pose->id}|".($mirrored ? 'm' : 's'));
        $existing = GeneratedImage::where('idempotency_key', $key)->first();
        if ($existing !== null && $existing->generation_status !== GenerationStatus::Failed) {
            return $existing;
        }

        $this->enforceDailyLimit($requester);

        $attributes = [
            'analysis_id' => $analysis->id,
            'pose_catalog_id' => $pose->id,
            'mirrored' => $mirrored,
            'generation_status' => GenerationStatus::Pending,
            'validation_status' => ValidationStatus::Unvalidated,
            'failure_message' => null,
            'consented_at' => now(),
        ];
        $image = $existing ?? new GeneratedImage(['idempotency_key' => $key]);
        $image->fill($attributes)->save();

        GeneratePoseImage::dispatch($image->id)->afterCommit();

        return $image;
    }

    private function enforceDailyLimit(Requester $requester): void
    {
        $limit = (int) config('figurepose.generation.daily_limit');
        $used = GeneratedImage::where('consented_at', '>=', now()->subDay())
            ->whereHas('analysis', fn ($q) => $requester->user !== null
                ? $q->where('user_id', $requester->user->id)
                : $q->whereNull('user_id')->where('guest_key_hash', Analysis::hashGuestKey((string) $requester->guestKey)))
            ->count();

        if ($used >= $limit) {
            throw new HttpException(429, "You've reached today's limit of {$limit} AI visuals. Try again tomorrow.");
        }
    }
}

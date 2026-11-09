<?php

namespace App\Jobs;

use App\Enums\AnalysisStatus;
use App\Models\Analysis;
use App\Services\AIService;
use App\Services\StorageService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;
use Throwable;

class ProcessFigureAnalysis implements ShouldQueue
{
    use Queueable;

    public int $timeout = 90;

    public int $tries = 3;

    public function __construct(public int $analysisId)
    {
        $this->tries = (int) config('figurepose.analysis.max_attempts', 3);
    }

    /** @return list<int> */
    public function backoff(): array
    {
        return [5, 15, 30];
    }

    public function handle(AIService $ai, StorageService $storage): void
    {
        $analysis = Analysis::with('profile')->find($this->analysisId);

        if ($analysis === null || $analysis->status->isFinal()) {
            return;
        }

        $analysis->update([
            'status' => AnalysisStatus::Processing,
            'attempts' => $analysis->attempts + 1,
            'started_at' => $analysis->started_at ?? now(),
        ]);

        $result = $ai->analyze(
            $storage->read($analysis->image_disk, $analysis->image_path),
            basename($analysis->image_path),
            $analysis->profile?->slug,
            $analysis->public_id,
        );

        $quality = $result['quality'] ?? [];

        // IMG-09: an unsuitable photo is a final, user-facing failure, not something to retry.
        if (! ($quality['ok'] ?? false)) {
            $issue = $quality['issues'][0] ?? ['code' => 'unsuitable_image', 'message' => 'This photo can\'t be analyzed.'];
            $analysis->update([
                'status' => AnalysisStatus::Failed,
                'quality' => $quality,
                'ai_model_version' => $result['model_version'] ?? null,
                'failure_code' => $issue['code'],
                'failure_message' => $issue['message'],
                'completed_at' => now(),
            ]);

            return;
        }

        $analysis->update([
            'status' => AnalysisStatus::Completed,
            'quality' => $quality,
            'pose_data' => ['stage' => $result['stage'] ?? null, 'pose' => $result['pose'] ?? null],
            'ai_model_version' => $result['model_version'] ?? null,
            'completed_at' => now(),
        ]);
    }

    /** Called once retries are exhausted (AI service down, storage error...). */
    public function failed(?Throwable $e): void
    {
        Log::warning('Analysis failed after retries', ['analysis_id' => $this->analysisId, 'error' => $e?->getMessage()]);

        Analysis::whereKey($this->analysisId)->update([
            'status' => AnalysisStatus::Failed,
            'failure_code' => 'ai_unavailable',
            'failure_message' => 'We couldn\'t analyze this photo right now. Try again in a few minutes.',
            'completed_at' => now(),
        ]);
    }
}

<?php

namespace App\Jobs;

use App\Models\PoseReference;
use App\Models\ReferenceSearch;
use App\Services\AIService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;
use Throwable;

/** Finds image URLs for a character on Pinterest, then reads each one in its own job (ReadPoseReference). */
class SearchPoseReferences implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;

    public int $timeout = 90;

    public function __construct(public int $searchId) {}

    public function handle(AIService $ai): void
    {
        $search = ReferenceSearch::find($this->searchId);
        if ($search === null || $search->status !== 'running') {
            return;
        }

        $urls = $ai->searchReferences($search->character_name.' figure', (int) config('figurepose.references.per_search'));
        // Images seen before (accepted or rejected) are not fetched again.
        $seen = PoseReference::whereIn('source_url_hash', array_map(fn ($u) => hash('sha256', $u), $urls))->pluck('source_url_hash')->all();
        $new = array_values(array_filter($urls, fn ($u) => ! in_array(hash('sha256', $u), $seen, true)));

        $search->update(['total' => count($new), 'checked' => 0, 'found' => 0]);
        if ($new === []) {
            $search->update(['status' => 'done', 'finished_at' => now()]);

            return;
        }
        foreach ($new as $url) {
            ReadPoseReference::dispatch($search->id, $url)->onQueue('references');
        }
    }

    public function failed(?Throwable $e): void
    {
        Log::warning('Reference search failed', ['search_id' => $this->searchId, 'error' => $e?->getMessage()]);
        ReferenceSearch::whereKey($this->searchId)->update([
            'status' => 'failed', 'error' => 'Pinterest search failed. Try again later.', 'finished_at' => now(),
        ]);
    }
}

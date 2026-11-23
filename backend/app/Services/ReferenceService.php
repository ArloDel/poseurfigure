<?php

namespace App\Services;

use App\Jobs\SearchPoseReferences;
use App\Models\Analysis;
use App\Models\ReferenceSearch;
use App\Support\CharacterKey;

/**
 * Pose references from Pinterest for a character (personal instances only: figurepose.references.pinterest).
 * One search per character, shared by every analysis of it; found images are kept, so the next analysis of
 * the same character gets them at once.
 */
class ReferenceService
{
    public function __construct(private readonly RecommendationService $recommendations) {}

    public function enabled(): bool
    {
        return (bool) config('figurepose.references.pinterest');
    }

    /** Starts (or restarts) the search for the analysis' character, unless a fresh one exists. */
    public function ensureSearch(Analysis $analysis): ?ReferenceSearch
    {
        $key = CharacterKey::from($analysis->character_name);
        if (! $this->enabled() || $key === '') {
            return null;
        }

        $search = ReferenceSearch::firstOrNew(['character_key' => $key]);
        $fresh = match ($search->status) {
            // A search stuck "running" for long lost its jobs (worker restarted): start over.
            'running' => $search->updated_at?->gt(now()->subMinutes(30)),
            'done' => $search->finished_at?->gt(now()->subDays((int) config('figurepose.references.refresh_days'))),
            'failed' => $search->finished_at?->gt(now()->subHour()),
            default => false,
        };
        if ($search->exists && $fresh) {
            return $search;
        }

        $search->fill([
            'character_name' => $analysis->character_name,
            'figure_profile_id' => $analysis->figure_profile_id,
            'status' => 'running', 'total' => 0, 'checked' => 0, 'found' => 0, 'error' => null, 'finished_at' => null,
        ])->save();
        SearchPoseReferences::dispatch($search->id)->onQueue('references');

        return $search;
    }

    public function searchFor(?string $characterName): ?ReferenceSearch
    {
        $key = CharacterKey::from($characterName);

        return $key === '' ? null : ReferenceSearch::where('character_key', $key)->first();
    }

    /** Ranks again the recent analyses of this character, so new references show up in their ideas. */
    public function refreshAnalyses(string $characterKey): void
    {
        Analysis::with('profile')
            ->whereNotNull('character_name')
            ->where('updated_at', '>', now()->subDays(3))
            ->latest('id')->limit(50)->get()
            ->filter(fn (Analysis $a) => CharacterKey::from($a->character_name) === $characterKey)
            ->each(fn (Analysis $a) => $this->recommendations->rerank($a));
    }
}

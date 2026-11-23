<?php

namespace App\Jobs;

use App\Models\PoseReference;
use App\Models\ReferenceSearch;
use App\Services\AIService;
use App\Services\ReferenceService;
use App\Services\StorageService;
use App\Support\CharacterKey;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Throwable;

/**
 * Reads one found image: the AI service downloads it and reads its pose. Accepted images are stored privately as
 * a reference for the character; rejected ones are remembered with the reason so they aren't fetched again.
 */
class ReadPoseReference implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    // One download plus one model run; below the queue's retry_after (150 s).
    public int $timeout = 120;

    /** Two references this alike are the same photo (a crop or re-upload). */
    private const DUPLICATE = 0.97;

    public function __construct(public int $searchId, public string $url) {}

    /** @return list<int> */
    public function backoff(): array
    {
        return [20];
    }

    public function handle(AIService $ai, StorageService $storage, ReferenceService $references): void
    {
        $search = ReferenceSearch::find($this->searchId);
        if ($search === null) {
            return;
        }
        $profile = $search->figure_profile_id ? \App\Models\FigureProfile::find($search->figure_profile_id)?->slug : null;
        $hash = hash('sha256', $this->url);

        if (! PoseReference::where('source_url_hash', $hash)->exists()) {
            $read = $ai->readReference($this->url, $profile ?? 'humanoid_v1');
            $base = [
                'character_key' => $search->character_key, 'character_name' => $search->character_name,
                'figure_profile_id' => $search->figure_profile_id, 'source' => 'pinterest',
                'source_url' => $this->url, 'source_url_hash' => $hash,
            ];

            if (($read['accepted'] ?? false) && $this->isDuplicate($search->character_key, $read['appearance'] ?? [])) {
                $read = ['accepted' => false, 'reason' => 'duplicate'];
            }

            if ($read['accepted'] ?? false) {
                $stored = $storage->storeReference(base64_decode($read['image_base64']), (string) Str::uuid());
                PoseReference::create($base + [
                    'status' => 'accepted',
                    'image_disk' => $stored['disk'], 'image_path' => $stored['path'],
                    'image_width' => $read['width'], 'image_height' => $read['height'],
                    'joint_positions' => [
                        'image_size' => [$read['width'], $read['height']],
                        'keypoints' => $read['keypoints'],
                        'joint_angles' => $read['joint_angles'] ?? [],
                        'orientation' => $read['orientation'] ?? null,
                    ],
                    'figure_box' => $read['figure_box'] ?? null,
                    'appearance' => ['embedding' => $read['appearance'], 'version' => $read['appearance_version'] ?? null],
                ]);
                $search->increment('found');
                $references->refreshAnalyses($search->character_key);
            } else {
                PoseReference::create($base + ['status' => 'rejected', 'reject_reason' => substr((string) ($read['reason'] ?? 'unknown'), 0, 40)]);
            }
        }

        $this->checked();
    }

    private function isDuplicate(string $key, array $embedding): bool
    {
        if ($embedding === []) {
            return false;
        }
        foreach (PoseReference::accepted()->where('character_key', $key)->pluck('appearance') as $look) {
            $other = $look['embedding'] ?? [];
            if (count($other) === count($embedding) && self::cosine($embedding, $other) >= self::DUPLICATE) {
                return true;
            }
        }

        return false;
    }

    private static function cosine(array $a, array $b): float
    {
        $dot = $na = $nb = 0.0;
        foreach ($a as $i => $x) {
            $dot += $x * $b[$i];
            $na += $x * $x;
            $nb += $b[$i] * $b[$i];
        }

        return $na > 0 && $nb > 0 ? $dot / sqrt($na * $nb) : 0.0;
    }

    /** One more image looked at; the search is done when all are. */
    private function checked(): void
    {
        DB::transaction(function () {
            $search = ReferenceSearch::lockForUpdate()->find($this->searchId);
            if ($search === null) {
                return;
            }
            $search->increment('checked');
            if ($search->checked >= $search->total && $search->status === 'running') {
                $search->update(['status' => 'done', 'finished_at' => now()]);
            }
        });
    }

    public function failed(?Throwable $e): void
    {
        // The image couldn't be read even after a retry: count it as looked at, so the search can finish.
        $this->checked();
    }
}

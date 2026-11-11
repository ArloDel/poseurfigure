<?php

namespace App\Services;

use App\Enums\AnalysisStatus;
use App\Models\Analysis;
use App\Models\PoseCatalog;

/** Ranks catalog poses for an analysis and stores them (PRD 9.3, REC-01..07). */
class RecommendationService
{
    public function __construct(private readonly AIService $ai) {}

    /**
     * Ranks published poses of the figure type, leaving out $excludeIds.
     *
     * @param  array<string, mixed>  $pose  the AI service's pose result
     * @param  list<int>  $excludeIds
     * @return array{rows: list<array<string, mixed>>, basis: string, remaining: int, matcher_version: ?string}
     */
    public function rank(Analysis $analysis, array $pose, string $profileSlug, array $excludeIds = []): array
    {
        $empty = ['rows' => [], 'basis' => 'pose', 'remaining' => 0, 'matcher_version' => null];

        $candidates = PoseCatalog::published()
            ->whereHas('profile', fn ($q) => $q->where('slug', $profileSlug))
            ->get()
            ->filter(fn (PoseCatalog $p) => isset($p->joint_positions['keypoints'], $p->joint_positions['image_size']))
            ->map(fn (PoseCatalog $p) => [
                'id' => $p->id,
                'keypoints' => $p->joint_positions['keypoints'],
                'image_size' => $p->joint_positions['image_size'],
                'category' => $p->category,
                'difficulty' => $p->difficulty,
            ])
            ->values()
            ->all();

        if ($candidates === [] || empty($pose['keypoints'])) {
            return $empty;
        }

        $result = $this->ai->recommend(
            $profileSlug,
            $pose['keypoints'],
            [$analysis->image_width, $analysis->image_height],
            $candidates,
            $analysis->figure?->articulation_config ?? [],
            (int) config('figurepose.recommendations.count'),
            $analysis->public_id,
            $excludeIds,
        );

        $rows = collect($result['results'] ?? [])->values()->map(fn (array $r, int $i) => [
            'pose_catalog_id' => $r['id'],
            'rank' => $i + 1,
            'similarity_score' => $r['similarity'],
            'feasibility_score' => $r['feasibility'],
            'score' => $r['score'],
            'details' => [
                'components' => $r['components'] ?? [],
                'shared_joints' => $r['shared_joints'] ?? null,
                'mirrored' => $r['mirrored'] ?? false,
                'warnings' => $r['warnings'] ?? [],
                'reasons' => $r['reasons'] ?? [],
                'matcher_version' => $result['matcher_version'] ?? null,
            ],
        ])->all();

        return [
            'rows' => $rows,
            'basis' => $result['basis'] ?? 'pose',
            'remaining' => (int) ($result['remaining'] ?? 0),
            'matcher_version' => $result['matcher_version'] ?? null,
        ];
    }

    /**
     * Stores a ranking as the analysis' current recommendations and remembers which poses were shown.
     *
     * @param  array{rows: list<array>, basis: string, remaining: int, matcher_version: ?string}  $ranking
     * @param  list<int>  $alreadyShown
     */
    public function replace(Analysis $analysis, array $ranking, array $alreadyShown = []): void
    {
        $analysis->recommendations()->delete();
        foreach ($ranking['rows'] as $row) {
            $analysis->recommendations()->create($row);
        }

        $data = $analysis->pose_data ?? [];
        $data['recommendation'] = [
            'basis' => $ranking['basis'],
            'remaining' => $ranking['remaining'],
            'matcher_version' => $ranking['matcher_version'],
            'shown_pose_ids' => array_values(array_unique([...$alreadyShown, ...array_column($ranking['rows'], 'pose_catalog_id')])),
        ];
        $analysis->update(['pose_data' => $data]);
    }

    /**
     * "Show different poses" (REC-07): the next best poses not shown yet.
     * Returns false when every pose for the figure type has been shown; the current list stays.
     */
    public function showDifferent(Analysis $analysis): bool
    {
        $pose = $analysis->pose_data['pose'] ?? null;
        $profile = $analysis->profile?->slug;
        if ($analysis->status !== AnalysisStatus::Completed || $pose === null || $profile === null) {
            return false;
        }

        $shown = $analysis->pose_data['recommendation']['shown_pose_ids']
            ?? $analysis->recommendations()->pluck('pose_catalog_id')->all();

        $ranking = $this->rank($analysis, $pose, $profile, $shown);
        if ($ranking['rows'] === []) {
            return false;
        }

        $this->replace($analysis, $ranking, $shown);

        return true;
    }
}

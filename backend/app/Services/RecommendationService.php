<?php

namespace App\Services;

use App\Models\Analysis;
use App\Models\PoseCatalog;

/** Ranks catalog poses for an analysis and stores them (PRD 9.3, REC-01..06). */
class RecommendationService
{
    public function __construct(private readonly AIService $ai) {}

    /**
     * Ranks published poses of the analysis' figure type. Returns rows ready to store,
     * or an empty list when the analysis has no usable pose or the catalog has no poses for the type.
     *
     * @param  array<string, mixed>  $pose  the AI service's pose result
     * @return list<array<string, mixed>>
     */
    public function rank(Analysis $analysis, array $pose, string $profileSlug): array
    {
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
            return [];
        }

        $result = $this->ai->recommend(
            $profileSlug,
            $pose['keypoints'],
            [$analysis->image_width, $analysis->image_height],
            $candidates,
            $analysis->figure?->articulation_config ?? [],
            (int) config('figurepose.recommendations.count'),
            $analysis->public_id,
        );

        return collect($result['results'] ?? [])->values()->map(fn (array $r, int $i) => [
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
                'matcher_version' => $result['matcher_version'] ?? null,
            ],
        ])->all();
    }

    /** @param  list<array<string, mixed>>  $rows */
    public function replace(Analysis $analysis, array $rows): void
    {
        $analysis->recommendations()->delete();
        foreach ($rows as $row) {
            $analysis->recommendations()->create($row);
        }
    }
}

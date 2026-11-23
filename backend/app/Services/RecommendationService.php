<?php

namespace App\Services;

use App\Enums\AnalysisStatus;
use App\Models\Analysis;
use App\Models\PoseCatalog;
use App\Models\PoseReference;

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
    public function rank(Analysis $analysis, array $pose, string $profileSlug, array $excludeIds = [], ?array $appearance = null): array
    {
        $empty = ['rows' => [], 'basis' => 'pose', 'remaining' => 0, 'matcher_version' => null];
        $appearance ??= $analysis->pose_data['appearance'] ?? null;

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
                'appearance' => $p->appearance['embedding'] ?? null,
                'character' => $p->character_name,
            ])
            ->values()
            ->all();

        // References found on Pinterest for this figure type (personal instances): negative ids keep them apart
        // from catalog poses. Only with pose ideas, which compare looks and characters.
        if (! empty($appearance['embedding'])) {
            $profileId = $analysis->figure_profile_id;
            foreach (PoseReference::accepted()->where('figure_profile_id', $profileId)->get() as $ref) {
                $candidates[] = [
                    'id' => -$ref->id,
                    'keypoints' => $ref->joint_positions['keypoints'],
                    'image_size' => $ref->joint_positions['image_size'],
                    'category' => 'pinterest',
                    'difficulty' => null,
                    'appearance' => $ref->appearance['embedding'] ?? null,
                    'character' => $ref->character_name,
                ];
            }
        }

        if ($candidates === [] || (empty($pose['keypoints']) && empty($appearance['embedding']))) {
            return $empty;
        }

        // Pose ideas: the same character first, then figures that look like this one (the product's core idea).
        // Older analyses without an appearance embedding keep the pose-matching ranking.
        if (! empty($appearance['embedding'])) {
            $result = $this->ai->inspire(
                $profileSlug,
                empty($pose['keypoints']) ? null : ['keypoints' => $pose['keypoints'], 'image_size' => [$analysis->image_width, $analysis->image_height]],
                $appearance['embedding'],
                $analysis->character_name,
                $candidates,
                $analysis->figure?->articulation_config ?? [],
                (int) config('figurepose.recommendations.ideas_count'),
                $analysis->public_id,
                $excludeIds,
            );

            return $this->rows($result);
        }

        foreach ($candidates as &$c) {
            unset($c['appearance'], $c['character']);
        }
        unset($c);

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

        return $this->rows($result);
    }

    /** @return array{rows: list<array<string, mixed>>, basis: string, remaining: int, matcher_version: ?string} */
    private function rows(array $result): array
    {
        $rows = collect($result['results'] ?? [])->values()->map(fn (array $r, int $i) => [
            'pose_catalog_id' => $r['id'] > 0 ? $r['id'] : null,
            'pose_reference_id' => $r['id'] < 0 ? -$r['id'] : null,
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
                'changes' => $r['changes'] ?? [],
                'group' => $r['group'] ?? null,
                'look' => $r['look'] ?? null,
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
            'shown_pose_ids' => array_values(array_unique([...$alreadyShown, ...array_map(
                fn (array $row) => $row['pose_reference_id'] ? -$row['pose_reference_id'] : $row['pose_catalog_id'],
                $ranking['rows'],
            )])),
        ];
        $analysis->update(['pose_data' => $data]);
    }

    /**
     * Ranks again from the top, e.g. after the user named the character, and forgets which poses were shown.
     */
    public function rerank(Analysis $analysis): void
    {
        $pose = $analysis->pose_data['pose'] ?? null;
        $profile = $analysis->profile?->slug;
        if ($analysis->status !== AnalysisStatus::Completed || $pose === null || $profile === null) {
            return;
        }
        $this->replace($analysis, $this->rank($analysis, $pose, $profile));
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
            ?? $analysis->recommendations()->get()->map->candidateId()->all();

        $ranking = $this->rank($analysis, $pose, $profile, $shown);
        if ($ranking['rows'] === []) {
            return false;
        }

        $this->replace($analysis, $ranking, $shown);

        return true;
    }
}

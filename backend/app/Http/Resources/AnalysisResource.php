<?php

namespace App\Http\Resources;

use App\Enums\AnalysisStatus;
use App\Models\ReferenceSearch;
use App\Support\CharacterKey;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Analysis */
class AnalysisResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $final = $this->status->isFinal();

        return [
            'analysis_id' => $this->public_id,
            'status' => $this->status->value,
            'analysis_mode' => $this->analysis_mode->value,
            'profile' => $this->profile?->slug,
            'image' => [
                'width' => $this->image_width,
                'height' => $this->image_height,
                'mime' => $this->image_mime,
                'size' => $this->image_size,
            ],
            'poll_after_seconds' => $this->when(! $final, config('figurepose.analysis.poll_after_seconds')),
            'quality' => $this->when($final, $this->quality),
            // Detection and pose results (PRD 8.3). Coordinates are normalized to the uploaded photo.
            'figures' => $this->when($this->status === AnalysisStatus::Completed, fn () => $this->pose_data['figures'] ?? []),
            'selected_figure' => $this->when($this->status === AnalysisStatus::Completed, fn () => $this->pose_data['selected_figure'] ?? null),
            'classification' => $this->when($this->status === AnalysisStatus::Completed, fn () => $this->pose_data['classification'] ?? null),
            'pose' => $this->when($this->status === AnalysisStatus::Completed, fn () => $this->pose_data['pose'] ?? null),
            'recommendations' => $this->when(
                $this->status === AnalysisStatus::Completed,
                fn () => $this->recommendations->map(fn ($r) => [
                    'rank' => $r->rank,
                    'score' => $r->score,
                    'similarity_score' => $r->similarity_score,
                    'feasibility_score' => $r->feasibility_score,
                    // The user's figure matches this pose with left and right swapped: "mirror it".
                    'mirrored' => (bool) ($r->details['mirrored'] ?? false),
                    'warnings' => $r->details['warnings'] ?? [],
                    // close_to_current, few_changes, new_direction, mirror, different_category, check_joints
                    'reasons' => $r->details['reasons'] ?? [],
                    // What to change on the user's figure, joint by joint, in their own left/right: keep, bend,
                    // straighten, raise, lower, lift_leg, lower_leg, unknown. Empty when ranked by figure type only.
                    'changes' => $r->details['changes'] ?? [],
                    // Pose ideas: same_character, similar_look or more; look = how alike the figures look (0-1).
                    'group' => $r->details['group'] ?? null,
                    'look' => $r->details['look'] ?? null,
                    'pose' => $r->pose_reference_id
                        ? (new ReferencePoseResource($r->reference))->resolve($request)
                        : (new PoseResource($r->pose))->resolve($request),
                ])->all(),
            ),
            // "pose": ranked against the figure's pose. "type_only": the pose couldn't be read, so these are
            // varied poses for the figure type, not matches; the app should say so.
            'recommendation_basis' => $this->when($this->status === AnalysisStatus::Completed,
                fn () => $this->pose_data['recommendation']['basis'] ?? 'pose'),
            'more_recommendations' => $this->when($this->status === AnalysisStatus::Completed,
                fn () => ($this->pose_data['recommendation']['remaining'] ?? 0) > 0),
            // The character the figure shows, if known: suggested by the vision model ("ai") or typed ("user").
            'character' => $this->when($this->status === AnalysisStatus::Completed, fn () => [
                'name' => $this->character_name,
                'source' => $this->character_source,
                'franchise' => $this->character_source === 'ai' ? ($this->character_details['franchise'] ?? null) : null,
                'confidence' => $this->character_source === 'ai' ? ($this->character_details['confidence'] ?? null) : null,
            ]),
            // Finding this character's poses on Pinterest (personal instances): progress for the app.
            'references' => $this->when($this->status === AnalysisStatus::Completed && config('figurepose.references.pinterest'),
                function () {
                    $key = CharacterKey::from($this->character_name);
                    $search = $key === '' ? null : ReferenceSearch::where('character_key', $key)->first();

                    // "found" counts every usable reference of this character, also from searches under a related
                    // name ("Spider Man symbiote suit" and "Spider-Man"); progress is this search's.
                    $found = \App\Models\PoseReference::accepted()->pluck('character_name')
                        ->filter(fn ($name) => CharacterKey::same($name, $this->character_name))->count();

                    return $search === null ? null : [
                        'status' => $search->status, 'total' => $search->total, 'checked' => $search->checked,
                        'found' => $search->status === 'running' ? $search->found : $found, 'error' => $search->error,
                    ];
                }),
            'character_recognition' => $this->when($this->status === AnalysisStatus::Completed, fn () => [
                'available' => (bool) config('figurepose.character.enabled'),
                'provider' => config('figurepose.character.provider_name'),
            ]),
            // Whether the app may offer "Make AI visual" for this analysis' recommendations.
            'ai_visuals_available' => $this->when($this->status === AnalysisStatus::Completed,
                (bool) config('figurepose.generation.enabled')),
            // Named in the consent sheet before the user sends their photo. Null: "an image service".
            'ai_visuals_provider' => $this->when($this->status === AnalysisStatus::Completed,
                config('figurepose.generation.provider_name')),
            'error' => $this->when($this->status === AnalysisStatus::Failed, fn () => [
                'code' => $this->failure_code,
                'message' => $this->failure_message,
                'retryable' => $this->failure_code === 'ai_unavailable',
            ]),
            'ai_model_version' => $this->ai_model_version,
            'created_at' => $this->created_at?->toIso8601String(),
            'completed_at' => $this->completed_at?->toIso8601String(),
        ];
    }
}

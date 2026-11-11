<?php

namespace App\Http\Resources;

use App\Enums\AnalysisStatus;
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
                    'pose' => (new PoseResource($r->pose))->resolve($request),
                ])->all(),
            ),
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

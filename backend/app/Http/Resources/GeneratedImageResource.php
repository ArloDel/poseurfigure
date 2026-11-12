<?php

namespace App\Http\Resources;

use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\URL;

/** @mixin \App\Models\GeneratedImage */
class GeneratedImageResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $ready = $this->generation_status === GenerationStatus::Generated && $this->image_path !== null;

        return [
            'id' => $this->id,
            'pose_id' => $this->pose_catalog_id,
            'analysis_id' => $this->analysis->public_id,
            'status' => $this->generation_status->value,          // pending | generated | failed
            'validation_status' => $this->validation_status->value, // unvalidated | validated | rejected
            // Always true: the app must label these images and never present them as catalog references (REC-09/10).
            'ai_generated' => true,
            'source' => 'ai_generated',
            'provider' => $this->provider,
            'mirrored' => $this->mirrored,
            'validation_note' => match (true) {
                ! $ready => null,
                $this->validation_status === ValidationStatus::Validated => 'The pose in this image matches the target pose. It is not proof your figure can hold it.',
                $this->validation_status === ValidationStatus::Rejected => "This image doesn't show the target pose reliably. Follow the catalog steps instead.",
                default => "This image hasn't been checked against the target pose.",
            },
            // Private file behind a link that expires (PRD 15.1).
            'image_url' => $ready ? URL::temporarySignedRoute(
                'generated-images.file',
                now()->addMinutes((int) config('figurepose.generation.url_ttl_minutes')),
                ['generatedImage' => $this->id],
            ) : null,
            'poll_after_seconds' => $this->generation_status === GenerationStatus::Pending ? 2 : null,
            'error' => $this->generation_status === GenerationStatus::Failed ? ['message' => $this->failure_message] : null,
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

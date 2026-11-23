<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\URL;

/**
 * A Pinterest reference in the shape of a catalog pose (PoseResource), so the app shows both the same way.
 *
 * @mixin \App\Models\PoseReference
 */
class ReferencePoseResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'kind' => 'reference',
            'slug' => 'reference-'.$this->id,
            'name' => $this->character_name,
            'category' => 'pinterest',
            'difficulty' => '',
            'profile' => $this->profile?->slug,
            // Found on Pinterest: not a curated catalog reference, and not AI-generated either.
            'source' => 'pinterest',
            'image_url' => URL::temporarySignedRoute('pose-references.image',
                now()->addMinutes((int) config('figurepose.references.url_ttl_minutes')), ['poseReference' => $this->id]),
            'image_credit' => null,
            'source_url' => $this->source_url,
        ];
    }
}

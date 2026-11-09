<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\PoseCatalog */
class PoseResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $detail = $request->route('pose') !== null;

        return [
            'id' => $this->id,
            'slug' => $this->slug,
            'name' => $this->name,
            'category' => $this->category,
            'difficulty' => $this->difficulty,
            'profile' => $this->whenLoaded('profile', fn () => $this->profile->slug),
            // Catalog references are curated; AI-generated images come from a separate resource (REC-10).
            'source' => 'catalog',
            'reference_image' => $this->reference_image,
            'description' => $this->when($detail, $this->description),
            'instructions' => $this->when($detail, $this->instructions),
            'joint_positions' => $this->when($detail, $this->joint_positions),
            'constraints' => $this->when($detail, $this->constraints),
        ];
    }
}

<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\FigureProfile */
class FigureProfileResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'slug' => $this->slug,
            'name' => $this->name,
            'category' => $this->category,
            'version' => $this->version,
            'keypoints' => $this->skeleton_config['keypoints'] ?? [],
            'connections' => $this->skeleton_config['connections'] ?? [],
            'angle_convention' => $this->skeleton_config['angle_convention'] ?? null,
        ];
    }
}

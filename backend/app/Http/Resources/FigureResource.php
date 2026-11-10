<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Figure */
class FigureResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'brand' => $this->brand,
            'profile' => $this->profile?->slug,
            'profile_name' => $this->profile?->name,
            'articulation_config' => $this->articulation_config,
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

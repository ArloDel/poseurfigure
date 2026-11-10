<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Favorite */
class FavoriteResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'pose' => (new PoseResource($this->pose))->resolve($request),
            'saved_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

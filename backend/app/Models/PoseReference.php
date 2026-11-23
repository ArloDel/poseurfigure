<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** A pose photo found on Pinterest for a character (personal instances only). */
#[Fillable([
    'character_key', 'character_name', 'figure_profile_id', 'source', 'source_url', 'source_url_hash', 'status',
    'reject_reason', 'image_disk', 'image_path', 'image_width', 'image_height', 'joint_positions', 'figure_box', 'appearance',
])]
class PoseReference extends Model
{
    protected function casts(): array
    {
        return [
            'joint_positions' => 'array',
            'figure_box' => 'array',
            'appearance' => 'array',
        ];
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(FigureProfile::class, 'figure_profile_id');
    }

    /** @param Builder<PoseReference> $query */
    public function scopeAccepted(Builder $query): void
    {
        $query->where('status', 'accepted');
    }
}

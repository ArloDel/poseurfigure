<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable([
    'figure_profile_id', 'slug', 'name', 'category', 'difficulty', 'description',
    'joint_positions', 'constraints', 'instructions', 'reference_image', 'reference_credit', 'is_published',
])]
class PoseCatalog extends Model
{
    protected $table = 'pose_catalog';

    protected function casts(): array
    {
        return [
            'joint_positions' => 'array',
            'constraints' => 'array',
            'instructions' => 'array',
            'reference_credit' => 'array',
            'is_published' => 'boolean',
        ];
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(FigureProfile::class, 'figure_profile_id');
    }

    public function scopePublished(Builder $query): void
    {
        $query->where('is_published', true);
    }
}

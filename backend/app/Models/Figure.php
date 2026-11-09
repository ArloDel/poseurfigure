<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

#[Fillable(['user_id', 'figure_profile_id', 'name', 'brand', 'articulation_config'])]
class Figure extends Model
{
    protected function casts(): array
    {
        return ['articulation_config' => 'array'];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(FigureProfile::class, 'figure_profile_id');
    }

    public function analyses(): HasMany
    {
        return $this->hasMany(Analysis::class);
    }
}

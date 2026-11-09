<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

#[Fillable(['slug', 'name', 'category', 'version', 'skeleton_config', 'is_active'])]
class FigureProfile extends Model
{
    protected function casts(): array
    {
        return [
            'skeleton_config' => 'array',
            'is_active' => 'boolean',
        ];
    }

    public function figures(): HasMany
    {
        return $this->hasMany(Figure::class);
    }

    public function poses(): HasMany
    {
        return $this->hasMany(PoseCatalog::class);
    }
}

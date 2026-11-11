<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable(['analysis_id', 'pose_catalog_id', 'rank', 'similarity_score', 'feasibility_score', 'score', 'details'])]
class PoseRecommendation extends Model
{
    protected function casts(): array
    {
        return [
            'similarity_score' => 'float',
            'feasibility_score' => 'float',
            'score' => 'float',
            'details' => 'array',
        ];
    }

    public function analysis(): BelongsTo
    {
        return $this->belongsTo(Analysis::class);
    }

    public function pose(): BelongsTo
    {
        return $this->belongsTo(PoseCatalog::class, 'pose_catalog_id');
    }
}

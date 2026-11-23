<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable(['analysis_id', 'pose_catalog_id', 'pose_reference_id', 'rank', 'similarity_score', 'feasibility_score', 'score', 'details'])]
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

    /** Set instead of pose when the idea is a reference found on Pinterest. */
    public function reference(): BelongsTo
    {
        return $this->belongsTo(PoseReference::class, 'pose_reference_id');
    }

    /** The id the matcher knows this idea by: catalog poses as is, references negative. */
    public function candidateId(): int
    {
        return $this->pose_reference_id ? -$this->pose_reference_id : (int) $this->pose_catalog_id;
    }
}

<?php

namespace App\Models;

use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable(['analysis_id', 'pose_catalog_id', 'image_path', 'provider', 'generation_status', 'validation_status', 'idempotency_key'])]
class GeneratedImage extends Model
{
    protected function casts(): array
    {
        return [
            'generation_status' => GenerationStatus::class,
            'validation_status' => ValidationStatus::class,
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

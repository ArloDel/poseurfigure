<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable(['user_id', 'pose_catalog_id', 'pose_reference_id'])]
class Favorite extends Model
{
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function pose(): BelongsTo
    {
        return $this->belongsTo(PoseCatalog::class, 'pose_catalog_id');
    }

    /** Set instead of pose when the favorite is a Pinterest reference. */
    public function reference(): BelongsTo
    {
        return $this->belongsTo(PoseReference::class, 'pose_reference_id');
    }
}

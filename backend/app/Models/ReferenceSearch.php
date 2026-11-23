<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

/** Progress of finding pose references for one character. */
#[Fillable(['character_key', 'character_name', 'figure_profile_id', 'status', 'total', 'checked', 'found', 'error', 'finished_at'])]
class ReferenceSearch extends Model
{
    protected function casts(): array
    {
        return ['finished_at' => 'datetime'];
    }
}

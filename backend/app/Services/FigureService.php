<?php

namespace App\Services;

use App\Models\Figure;
use App\Models\User;
use Illuminate\Database\Eloquent\Collection;

class FigureService
{
    /** @return Collection<int, Figure> */
    public function listFor(User $user): Collection
    {
        return $user->figures()->with('profile')->latest('id')->get();
    }

    /** @param array{name: string, brand?: ?string, figure_profile_id: int, articulation_config?: ?array} $data */
    public function create(User $user, array $data): Figure
    {
        return $user->figures()->create($data)->load('profile');
    }
}

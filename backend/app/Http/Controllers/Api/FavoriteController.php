<?php

namespace App\Http\Controllers\Api;

use App\Http\Resources\FavoriteResource;
use App\Models\Favorite;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

/** Favorites are catalog poses saved to an account (FAV-01..03, AUTH-06). */
class FavoriteController extends ApiController
{
    public function index(Request $request): JsonResponse
    {
        $favorites = $request->user()->favorites()
            ->whereHas('pose', fn ($q) => $q->where('is_published', true))
            ->with('pose.profile')
            ->latest('id')
            ->get();

        return $this->ok(FavoriteResource::collection($favorites));
    }

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'pose_id' => ['required', 'integer', Rule::exists('pose_catalog', 'id')->where('is_published', true)],
        ], ['pose_id.exists' => 'That pose is not in the catalog.']);

        // Saving the same pose twice is not an error: the app can retry safely.
        $favorite = $request->user()->favorites()->firstOrCreate(['pose_catalog_id' => $data['pose_id']]);

        return $this->ok(
            new FavoriteResource($favorite->load('pose.profile')),
            'Saved to favorites',
            $favorite->wasRecentlyCreated ? 201 : 200,
        );
    }

    public function destroy(Request $request, Favorite $favorite): JsonResponse
    {
        abort_unless($favorite->user_id === $request->user()->id, 404);

        $favorite->delete();

        return $this->ok(null, 'Removed from favorites');
    }
}

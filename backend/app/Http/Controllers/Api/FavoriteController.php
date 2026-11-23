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
            ->where(fn ($q) => $q->whereHas('pose', fn ($p) => $p->where('is_published', true))
                ->orWhereHas('reference', fn ($r) => $r->where('status', 'accepted')))
            ->with(['pose.profile', 'reference.profile'])
            ->latest('id')
            ->get();

        return $this->ok(FavoriteResource::collection($favorites));
    }

    public function store(Request $request): JsonResponse
    {
        // A catalog pose (pose_id) or a Pinterest reference (reference_id).
        $data = $request->validate([
            'pose_id' => ['required_without:reference_id', 'prohibits:reference_id', 'integer',
                Rule::exists('pose_catalog', 'id')->where('is_published', true)],
            'reference_id' => ['required_without:pose_id', 'integer', Rule::exists('pose_references', 'id')->where('status', 'accepted')],
        ], ['pose_id.exists' => 'That pose is not in the catalog.', 'reference_id.exists' => 'That reference is no longer available.']);

        // Saving the same pose twice is not an error: the app can retry safely.
        $favorite = $request->user()->favorites()->firstOrCreate(isset($data['reference_id'])
            ? ['pose_reference_id' => $data['reference_id']]
            : ['pose_catalog_id' => $data['pose_id']]);

        return $this->ok(
            new FavoriteResource($favorite->load(['pose.profile', 'reference.profile'])),
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

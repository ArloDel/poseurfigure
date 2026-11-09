<?php

namespace App\Http\Controllers\Api;

use App\Http\Resources\PoseResource;
use App\Models\PoseCatalog;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class PoseController extends ApiController
{
    public function index(Request $request): JsonResponse
    {
        $request->validate([
            'profile' => ['nullable', 'string', 'max:40'],
            'category' => ['nullable', 'string', 'max:32'],
            'q' => ['nullable', 'string', 'max:80'],
        ]);

        $poses = PoseCatalog::published()
            ->with('profile')
            ->when($request->query('profile'), fn ($q, $slug) => $q->whereHas('profile', fn ($p) => $p->where('slug', $slug)))
            ->when($request->query('category'), fn ($q, $cat) => $q->where('category', $cat))
            ->when($request->query('q'), fn ($q, $term) => $q->where('name', 'like', '%'.addcslashes($term, '%_').'%'))
            ->orderBy('name')
            ->paginate(24);

        return response()->json([
            'success' => true,
            'data' => PoseResource::collection($poses->getCollection())->resolve($request),
            'meta' => ['current_page' => $poses->currentPage(), 'last_page' => $poses->lastPage(), 'total' => $poses->total()],
        ]);
    }

    public function show(PoseCatalog $pose): JsonResponse
    {
        abort_unless($pose->is_published, 404);

        return $this->ok(new PoseResource($pose->load('profile')));
    }
}

<?php

namespace App\Http\Controllers\Api;

use App\Enums\AnalysisMode;
use App\Http\Requests\StoreAnalysisRequest;
use App\Http\Resources\AnalysisResource;
use App\Models\Analysis;
use App\Services\AnalysisService;
use App\Support\Requester;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AnalysisController extends ApiController
{
    public function __construct(private readonly AnalysisService $analyses) {}

    public function store(StoreAnalysisRequest $request): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($requester->isIdentified(), 401, 'Sign in, or send an X-Guest-Key header (a UUID) to try without an account.');

        $analysis = $this->analyses->start(
            $request->file('image'),
            $requester,
            AnalysisMode::from($request->validated('analysis_mode')),
            $request->validated('figure_profile_id'),
            $request->validated('figure_id'),
        );

        return $this->ok([
            'analysis_id' => $analysis->public_id,
            'status' => $analysis->status->value,
            'poll_after_seconds' => config('figurepose.analysis.poll_after_seconds'),
        ], 'Analysis started', 202);
    }

    public function index(Request $request): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($requester->isIdentified(), 401, 'Sign in, or send an X-Guest-Key header (a UUID) to see your history.');

        $page = $this->analyses->historyFor($requester);

        return response()->json([
            'success' => true,
            'data' => AnalysisResource::collection($page->getCollection())->resolve($request),
            'meta' => ['current_page' => $page->currentPage(), 'last_page' => $page->lastPage(), 'total' => $page->total()],
        ]);
    }

    public function destroy(Request $request, Analysis $analysis): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);

        $this->analyses->delete($analysis);

        return $this->ok(null, 'Analysis and photo deleted');
    }

    public function show(Request $request, Analysis $analysis): JsonResponse
    {
        $requester = Requester::fromRequest($request);

        // Same 404 for "missing" and "not yours", so ids can't be probed.
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);

        $analysis->load(['profile', 'recommendations.pose.profile']);

        return $this->ok(new AnalysisResource($analysis));
    }
}

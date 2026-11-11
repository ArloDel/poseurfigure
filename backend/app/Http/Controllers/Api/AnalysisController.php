<?php

namespace App\Http\Controllers\Api;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Http\Requests\StoreAnalysisRequest;
use App\Http\Resources\AnalysisResource;
use App\Models\Analysis;
use App\Services\AnalysisService;
use App\Services\RecommendationService;
use App\Support\Requester;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

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

    /**
     * The user confirms or corrects the figure type (FIG-03). The photo is analyzed again with that
     * type's skeleton; the response is the pending analysis, like a new upload.
     */
    public function confirmProfile(Request $request, Analysis $analysis): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);

        $data = $request->validate([
            'figure_profile_id' => ['required', 'integer', Rule::exists('figure_profiles', 'id')->where('is_active', true)],
        ], ['figure_profile_id.exists' => 'Pick one of the supported figure types.']);

        abort_unless($analysis->status === AnalysisStatus::Completed, 409, 'Only a finished analysis can be re-run with another figure type.');

        $this->analyses->rerunWithProfile($analysis, (int) $data['figure_profile_id']);

        return $this->ok([
            'analysis_id' => $analysis->public_id,
            'status' => $analysis->status->value,
            'poll_after_seconds' => config('figurepose.analysis.poll_after_seconds'),
        ], 'Analyzing again with the chosen figure type', 202);
    }

    /** "Show different poses" (REC-07): replaces the list with poses not shown yet. */
    public function showDifferent(Request $request, Analysis $analysis, RecommendationService $recommendations): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);
        abort_unless($analysis->status === AnalysisStatus::Completed, 409, 'The analysis is not finished yet.');

        $changed = $recommendations->showDifferent($analysis);
        $analysis->refresh()->load(['profile', 'recommendations.pose.profile']);

        return $this->ok(
            new AnalysisResource($analysis),
            $changed ? 'Here are different poses' : "You've seen every pose we have for this figure type",
        );
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

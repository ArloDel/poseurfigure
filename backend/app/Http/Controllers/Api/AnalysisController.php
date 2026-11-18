<?php

namespace App\Http\Controllers\Api;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Http\Requests\StoreAnalysisRequest;
use App\Http\Resources\AnalysisResource;
use App\Models\Analysis;
use App\Services\AnalysisService;
use App\Services\AIService;
use App\Services\RecommendationService;
use App\Services\StorageService;
use App\Support\Requester;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
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
    /**
     * Suggests the character the figure shows, with the vision model (the photo leaves the server: consent
     * required), then ranks pose ideas again with that character first. Low-confidence answers are kept as a
     * hint but not used; the user can always type or correct the name (setCharacter).
     */
    public function recognizeCharacter(Request $request, Analysis $analysis, AIService $ai, StorageService $storage, RecommendationService $recommendations): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);
        abort_unless((bool) config('figurepose.character.enabled'), 503, 'Character recognition is not available on this server.');
        $request->validate(['consent' => ['accepted']], [
            'consent.accepted' => 'Agree to send your photo to the recognition service first.',
        ]);
        abort_unless($analysis->status === AnalysisStatus::Completed, 409, 'The analysis is not finished yet.');

        $figures = $analysis->pose_data['figures'] ?? [];
        $bbox = $figures[$analysis->pose_data['selected_figure'] ?? 0]['bbox'] ?? null;
        try {
            $found = $ai->identify($storage->read($analysis->image_disk, $analysis->image_path),
                basename($analysis->image_path), $bbox, $analysis->public_id);
        } catch (RequestException $e) {
            abort_if($e->response->status() === 422, 422, 'The recognition service declined this photo. Type the name instead.');
            abort(503, "We couldn't recognize the character right now. Try again, or type the name.");
        } catch (ConnectionException) {
            abort(503, "We couldn't recognize the character right now. Try again, or type the name.");
        }

        $sure = ($found['confidence'] ?? 'low') !== 'low' && ($found['display_name'] ?? '') !== '';
        $analysis->update([
            'character_details' => array_intersect_key($found, array_flip(['character', 'variant', 'franchise', 'figure_line', 'display_name', 'confidence', 'model', 'provider'])),
            'character_name' => $sure ? $found['display_name'] : $analysis->character_name,
            'character_source' => $sure ? 'ai' : $analysis->character_source,
        ]);
        if ($sure) {
            $recommendations->rerank($analysis);
        }
        $analysis->refresh()->load(['profile', 'recommendations.pose.profile']);

        return $this->ok(new AnalysisResource($analysis),
            $sure ? "Looks like {$found['display_name']}. Not right? Change it." : "We couldn't tell who this is. Type the name to see that character's poses.");
    }

    /** The user names (or corrects, or clears) the character; pose ideas are ranked again with it first. */
    public function setCharacter(Request $request, Analysis $analysis, RecommendationService $recommendations): JsonResponse
    {
        $requester = Requester::fromRequest($request);
        abort_unless($analysis->isOwnedBy($requester->user, $requester->guestKey), 404);
        $data = $request->validate(['name' => ['present', 'nullable', 'string', 'max:120']]);
        abort_unless($analysis->status === AnalysisStatus::Completed, 409, 'The analysis is not finished yet.');

        $name = trim((string) ($data['name'] ?? ''));
        $analysis->update(['character_name' => $name === '' ? null : $name, 'character_source' => $name === '' ? null : 'user']);
        $recommendations->rerank($analysis);
        $analysis->refresh()->load(['profile', 'recommendations.pose.profile']);

        return $this->ok(new AnalysisResource($analysis), $name === '' ? 'Character cleared' : 'Showing poses of '.$name.' first');
    }

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

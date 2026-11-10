<?php

namespace App\Services;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Models\User;
use App\Support\Requester;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Str;

class AnalysisService
{
    public function __construct(private readonly StorageService $storage) {}

    /** Stores the photo, records a pending analysis and queues the AI work. Returns at once (PRD 11.4). */
    public function start(
        UploadedFile $image,
        Requester $requester,
        AnalysisMode $mode,
        ?int $profileId = null,
        ?int $figureId = null,
    ): Analysis {
        $publicId = (string) Str::uuid();
        [$width, $height] = getimagesize($image->getRealPath()) ?: [0, 0];
        $stored = $this->storage->storeUserImage($image, $publicId);

        $analysis = Analysis::create([
            'public_id' => $publicId,
            'user_id' => $requester->user?->id,
            'guest_key_hash' => $requester->user ? null : Analysis::hashGuestKey((string) $requester->guestKey),
            'figure_id' => $figureId,
            'figure_profile_id' => $profileId,
            'analysis_mode' => $mode,
            'status' => AnalysisStatus::Pending,
            'image_disk' => $stored['disk'],
            'image_path' => $stored['path'],
            'image_mime' => $image->getMimeType(),
            'image_size' => $image->getSize(),
            'image_width' => $width,
            'image_height' => $height,
        ]);

        ProcessFigureAnalysis::dispatch($analysis->id)->afterCommit();

        return $analysis;
    }

    /** Re-analyzes the stored photo with a type the user picked (FIG-03). */
    public function rerunWithProfile(Analysis $analysis, int $profileId): void
    {
        $analysis->update([
            'analysis_mode' => AnalysisMode::Manual,
            'figure_profile_id' => $profileId,
            'status' => AnalysisStatus::Pending,
            'pose_data' => null,
            'failure_code' => null,
            'failure_message' => null,
            'attempts' => 0,
            'started_at' => null,
            'completed_at' => null,
        ]);
        $analysis->recommendations()->delete();

        ProcessFigureAnalysis::dispatch($analysis->id)->afterCommit();
    }

    /** Previous analyses of a signed-in user, or of a guest device, newest first (HIST-01). */
    public function historyFor(Requester $requester, int $perPage = 20): LengthAwarePaginator
    {
        return Analysis::query()
            ->when(
                $requester->user !== null,
                fn ($q) => $q->where('user_id', $requester->user->id),
                fn ($q) => $q->whereNull('user_id')->where('guest_key_hash', Analysis::hashGuestKey((string) $requester->guestKey)),
            )
            ->with(['profile', 'recommendations.pose.profile'])
            ->latest('id')
            ->paginate($perPage);
    }

    /** Removes the analysis together with the user's photo (HIST-03, PRD 15.1). */
    public function delete(Analysis $analysis): void
    {
        $this->storage->delete($analysis->image_disk, $analysis->image_path);
        $analysis->delete();
    }

    /**
     * Moves analyses made as a guest on this device to the user's account,
     * so history survives signing up or signing in. Returns how many moved.
     */
    public function claimGuestAnalyses(User $user, string $guestKey): int
    {
        return Analysis::whereNull('user_id')
            ->where('guest_key_hash', Analysis::hashGuestKey($guestKey))
            ->update(['user_id' => $user->id, 'guest_key_hash' => null]);
    }
}

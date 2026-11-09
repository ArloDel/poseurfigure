<?php

namespace App\Services;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use App\Support\Requester;
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
}

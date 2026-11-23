<?php

namespace App\Http\Controllers\Api;

use App\Http\Resources\ReferencePoseResource;
use App\Models\PoseReference;
use App\Services\StorageService;
use Illuminate\Http\JsonResponse;
use Symfony\Component\HttpFoundation\Response;

/** Pinterest references: one reference's details, and its image behind a signed, expiring link (the file stays private). */
class PoseReferenceController extends ApiController
{
    /** One reference, e.g. opened from Favorites (no analysis around it). */
    public function show(PoseReference $poseReference): JsonResponse
    {
        abort_unless($poseReference->status === 'accepted', 404);

        return $this->ok(new ReferencePoseResource($poseReference->load('profile')));
    }

    public function image(PoseReference $poseReference, StorageService $storage): Response
    {
        abort_unless($poseReference->status === 'accepted' && $poseReference->image_path !== null, 404);

        return response($storage->read($poseReference->image_disk, $poseReference->image_path), 200, [
            'Content-Type' => 'image/jpeg',
            'Cache-Control' => 'private, max-age=3600',
        ]);
    }
}

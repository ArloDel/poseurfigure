<?php

namespace App\Http\Controllers\Api;

use App\Models\PoseReference;
use App\Services\StorageService;
use Symfony\Component\HttpFoundation\Response;

/** Serves a Pinterest reference image behind a signed, expiring link (the file itself stays private). */
class PoseReferenceController extends ApiController
{
    public function image(PoseReference $poseReference, StorageService $storage): Response
    {
        abort_unless($poseReference->status === 'accepted' && $poseReference->image_path !== null, 404);

        return response($storage->read($poseReference->image_disk, $poseReference->image_path), 200, [
            'Content-Type' => 'image/jpeg',
            'Cache-Control' => 'private, max-age=3600',
        ]);
    }
}

<?php

namespace App\Http\Controllers\Api;

use App\Enums\GenerationStatus;
use App\Http\Resources\GeneratedImageResource;
use App\Models\Analysis;
use App\Models\GeneratedImage;
use App\Models\PoseCatalog;
use App\Services\GenerationService;
use App\Services\StorageService;
use App\Support\Requester;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class GeneratedImageController extends ApiController
{
    /** POST /poses/{pose}/generate: an AI visual of the user's figure in this pose. */
    public function store(Request $request, PoseCatalog $pose, GenerationService $generation): JsonResponse
    {
        $data = $request->validate([
            'analysis_id' => ['required', 'uuid'],
            // PRD 15.1: explicit consent before the photo goes to a third-party image service.
            'consent' => ['accepted'],
            'mirrored' => ['sometimes', 'boolean'],
        ], ['consent.accepted' => 'Agree to send your photo to the image service to make an AI visual.']);

        $requester = Requester::fromRequest($request);
        $analysis = Analysis::where('public_id', $data['analysis_id'])->first();
        abort_unless($analysis !== null && $analysis->isOwnedBy($requester->user, $requester->guestKey), 404);

        $image = $generation->request($analysis, $pose, (bool) ($data['mirrored'] ?? false), $requester);

        return $this->ok(
            new GeneratedImageResource($image->load('analysis')),
            $image->wasRecentlyCreated ? 'Making your AI visual' : null,
            $image->generation_status === GenerationStatus::Pending ? 202 : 200,
        );
    }

    public function show(Request $request, GeneratedImage $generatedImage): JsonResponse
    {
        $this->authorizeOwner($request, $generatedImage);

        return $this->ok(new GeneratedImageResource($generatedImage));
    }

    /** The image itself. Reached only through a signed, expiring link, so no headers are needed to load it. */
    public function file(GeneratedImage $generatedImage, StorageService $storage): Response
    {
        abort_unless($generatedImage->generation_status === GenerationStatus::Generated && $generatedImage->image_path, 404);

        return response($storage->read($generatedImage->image_disk, $generatedImage->image_path), 200, [
            'Content-Type' => 'image/jpeg',
            'Cache-Control' => 'private, max-age=600',
            'X-Robots-Tag' => 'noindex',
        ]);
    }

    private function authorizeOwner(Request $request, GeneratedImage $image): void
    {
        $requester = Requester::fromRequest($request);
        abort_unless($image->analysis->isOwnedBy($requester->user, $requester->guestKey), 404);
    }
}

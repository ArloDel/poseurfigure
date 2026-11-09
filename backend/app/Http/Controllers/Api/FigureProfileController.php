<?php

namespace App\Http\Controllers\Api;

use App\Http\Resources\FigureProfileResource;
use App\Models\FigureProfile;
use Illuminate\Http\JsonResponse;

class FigureProfileController extends ApiController
{
    public function index(): JsonResponse
    {
        return $this->ok(FigureProfileResource::collection(
            FigureProfile::where('is_active', true)->orderBy('id')->get(),
        ));
    }
}

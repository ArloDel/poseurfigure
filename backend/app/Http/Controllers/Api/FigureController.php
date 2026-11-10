<?php

namespace App\Http\Controllers\Api;

use App\Http\Requests\StoreFigureRequest;
use App\Http\Resources\FigureResource;
use App\Services\FigureService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class FigureController extends ApiController
{
    public function __construct(private readonly FigureService $figures) {}

    public function index(Request $request): JsonResponse
    {
        return $this->ok(FigureResource::collection($this->figures->listFor($request->user())));
    }

    public function store(StoreFigureRequest $request): JsonResponse
    {
        $figure = $this->figures->create($request->user(), $request->validated());

        return $this->ok(new FigureResource($figure), 'Figure added', 201);
    }
}

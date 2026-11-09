<?php

use App\Http\Controllers\Api\AnalysisController;
use App\Http\Controllers\Api\FigureProfileController;
use App\Http\Controllers\Api\HealthController;
use App\Http\Controllers\Api\PoseController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    Route::get('/health', HealthController::class);

    Route::get('/figures/profiles', [FigureProfileController::class, 'index']);

    Route::get('/poses', [PoseController::class, 'index']);
    Route::get('/poses/{pose}', [PoseController::class, 'show'])->whereNumber('pose');

    Route::post('/analyses', [AnalysisController::class, 'store'])->middleware('throttle:analyses');
    Route::get('/analyses/{analysis}', [AnalysisController::class, 'show'])->whereUuid('analysis');

    // Sprint 2: auth (register/login), figures, favorites.
});

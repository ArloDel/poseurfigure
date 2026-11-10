<?php

use App\Http\Controllers\Api\AnalysisController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\FigureProfileController;
use App\Http\Controllers\Api\HealthController;
use App\Http\Controllers\Api\PoseController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    Route::get('/health', HealthController::class);

    Route::prefix('auth')->group(function () {
        Route::post('/register', [AuthController::class, 'register'])->middleware('throttle:auth');
        Route::post('/login', [AuthController::class, 'login'])->middleware('throttle:auth');

        Route::middleware('auth:sanctum')->group(function () {
            Route::post('/logout', [AuthController::class, 'logout']);
            Route::get('/me', [AuthController::class, 'me']);
        });
    });

    Route::get('/figures/profiles', [FigureProfileController::class, 'index']);

    Route::get('/poses', [PoseController::class, 'index']);
    Route::get('/poses/{pose}', [PoseController::class, 'show'])->whereNumber('pose');

    // Analyses work for guests too (X-Guest-Key), so they are not behind auth:sanctum.
    Route::post('/analyses', [AnalysisController::class, 'store'])->middleware('throttle:analyses');
    Route::get('/analyses/{analysis}', [AnalysisController::class, 'show'])->whereUuid('analysis');
});

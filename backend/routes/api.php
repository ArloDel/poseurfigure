<?php

use App\Http\Controllers\Api\AnalysisController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\FavoriteController;
use App\Http\Controllers\Api\FigureController;
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

    Route::middleware('auth:sanctum')->group(function () {
        Route::get('/figures', [FigureController::class, 'index']);
        Route::post('/figures', [FigureController::class, 'store']);

        Route::get('/favorites', [FavoriteController::class, 'index']);
        Route::post('/favorites', [FavoriteController::class, 'store']);
        Route::delete('/favorites/{favorite}', [FavoriteController::class, 'destroy'])->whereNumber('favorite');
    });

    Route::get('/poses', [PoseController::class, 'index']);
    Route::get('/poses/{pose}', [PoseController::class, 'show'])->whereNumber('pose');

    // Analyses work for guests too (X-Guest-Key), so they are not behind auth:sanctum.
    Route::post('/analyses', [AnalysisController::class, 'store'])->middleware('throttle:analyses');
    Route::get('/analyses', [AnalysisController::class, 'index']);
    Route::get('/analyses/{analysis}', [AnalysisController::class, 'show'])->whereUuid('analysis');
    Route::delete('/analyses/{analysis}', [AnalysisController::class, 'destroy'])->whereUuid('analysis');
    Route::post('/analyses/{analysis}/recommendations', [AnalysisController::class, 'showDifferent'])
        ->whereUuid('analysis')->middleware('throttle:analyses');
    Route::post('/analyses/{analysis}/profile', [AnalysisController::class, 'confirmProfile'])
        ->whereUuid('analysis')->middleware('throttle:analyses');
});

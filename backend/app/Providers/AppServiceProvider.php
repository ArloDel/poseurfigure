<?php

namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        // Uploads trigger AI work, so they are limited per user, guest device and IP.
        RateLimiter::for('analyses', function (Request $request) {
            $key = $request->user('sanctum')?->id ?? $request->header('X-Guest-Key') ?? $request->ip();

            return [
                Limit::perMinute(10)->by('analyses:'.$key),
                Limit::perMinute(30)->by('analyses-ip:'.$request->ip()),
            ];
        });
    }
}

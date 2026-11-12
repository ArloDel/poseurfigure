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
        // Slows down password guessing: per email + IP, and per IP overall.
        RateLimiter::for('auth', function (Request $request) {
            $email = mb_strtolower((string) $request->input('email'));

            return [
                Limit::perMinute(5)->by('auth:'.$email.'|'.$request->ip()),
                Limit::perMinute(20)->by('auth-ip:'.$request->ip()),
            ];
        });

        // AI visuals cost money per image: tighter than uploads. A daily cap is enforced in GenerationService.
        RateLimiter::for('generation', function (Request $request) {
            $key = $request->user('sanctum')?->id ?? $request->header('X-Guest-Key') ?? $request->ip();

            return Limit::perMinute(5)->by('generation:'.$key);
        });

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

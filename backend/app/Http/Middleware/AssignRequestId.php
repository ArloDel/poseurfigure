<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

/**
 * Tags every log line of a request with its ID (PRD: structured logs and request IDs).
 * nginx sets X-Request-Id; without it (dev server, tests) one is made here. The client gets it back,
 * so a user's bug report can be matched to the server logs.
 */
class AssignRequestId
{
    public function handle(Request $request, Closure $next): Response
    {
        $id = (string) $request->headers->get('X-Request-Id', '');
        // Only accept short, plain IDs from outside: the value ends up in logs.
        if (! preg_match('/^[A-Za-z0-9._-]{8,64}$/', $id)) {
            $id = (string) Str::uuid();
            $request->headers->set('X-Request-Id', $id);
        }

        Log::withContext(['request_id' => $id]);

        $response = $next($request);
        if (! $response->headers->has('X-Request-Id')) {
            $response->headers->set('X-Request-Id', $id);
        }

        return $response;
    }
}

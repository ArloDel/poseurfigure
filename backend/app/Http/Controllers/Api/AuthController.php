<?php

namespace App\Http\Controllers\Api;

use App\Http\Requests\LoginRequest;
use App\Http\Requests\RegisterRequest;
use App\Http\Resources\UserResource;
use App\Models\User;
use App\Services\AnalysisService;
use App\Support\Requester;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AuthController extends ApiController
{
    public function __construct(private readonly AnalysisService $analyses) {}

    public function register(RegisterRequest $request): JsonResponse
    {
        $user = User::create($request->safe()->only(['name', 'email', 'password']));

        return $this->tokenResponse($user, $request, 'Account created', 201);
    }

    public function login(LoginRequest $request): JsonResponse
    {
        $user = User::where('email', $request->validated('email'))->first();

        // Same message for a wrong email and a wrong password, so accounts can't be probed.
        if ($user === null || ! Hash::check($request->validated('password'), $user->password)) {
            throw ValidationException::withMessages(['email' => ["That email and password don't match."]]);
        }

        return $this->tokenResponse($user, $request, 'Signed in');
    }

    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return $this->ok(null, 'Signed out');
    }

    public function me(Request $request): JsonResponse
    {
        return $this->ok(new UserResource($request->user()));
    }

    private function tokenResponse(User $user, Request $request, string $message, int $status = 200): JsonResponse
    {
        $guestKey = Requester::fromRequest($request)->guestKey;
        $claimed = $guestKey !== null ? $this->analyses->claimGuestAnalyses($user, $guestKey) : 0;

        return $this->ok([
            'token' => $user->createToken($request->input('device_name') ?: 'mobile')->plainTextToken,
            'token_type' => 'Bearer',
            'user' => (new UserResource($user))->resolve($request),
            'claimed_analyses' => $claimed,
        ], $message, $status);
    }
}

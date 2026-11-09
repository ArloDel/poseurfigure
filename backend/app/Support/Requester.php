<?php

namespace App\Support;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

/**
 * Who is calling: a signed-in user (Sanctum token) or a guest device (AUTH-05).
 * Guests send a random UUID in the X-Guest-Key header, generated once and kept in secure storage on the device.
 */
final readonly class Requester
{
    public const GUEST_HEADER = 'X-Guest-Key';

    public function __construct(
        public ?User $user,
        public ?string $guestKey,
    ) {}

    public static function fromRequest(Request $request): self
    {
        $user = $request->user('sanctum');
        $key = $request->header(self::GUEST_HEADER);

        return new self($user, is_string($key) && Str::isUuid($key) ? $key : null);
    }

    public function isIdentified(): bool
    {
        return $this->user !== null || $this->guestKey !== null;
    }
}

<?php

namespace App\Models;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

#[Fillable([
    'public_id', 'user_id', 'guest_key_hash', 'figure_id', 'figure_profile_id', 'analysis_mode', 'status',
    'image_disk', 'image_path', 'image_mime', 'image_size', 'image_width', 'image_height',
    'pose_data', 'quality', 'ai_model_version', 'failure_code', 'failure_message',
    'attempts', 'started_at', 'completed_at',
])]
class Analysis extends Model
{
    protected $table = 'analyses';

    protected static function booted(): void
    {
        static::creating(function (Analysis $analysis) {
            $analysis->public_id ??= (string) Str::uuid();
        });
    }

    protected function casts(): array
    {
        return [
            'analysis_mode' => AnalysisMode::class,
            'status' => AnalysisStatus::class,
            'pose_data' => 'array',
            'quality' => 'array',
            'started_at' => 'datetime',
            'completed_at' => 'datetime',
        ];
    }

    /** Public URLs use the UUID, never the sequential id. */
    public function getRouteKeyName(): string
    {
        return 'public_id';
    }

    public static function hashGuestKey(string $key): string
    {
        return hash_hmac('sha256', $key, (string) config('app.key'));
    }

    public function isOwnedBy(?User $user, ?string $guestKey): bool
    {
        if ($this->user_id !== null) {
            return $user !== null && $user->id === $this->user_id;
        }

        return $guestKey !== null
            && $this->guest_key_hash !== null
            && hash_equals($this->guest_key_hash, self::hashGuestKey($guestKey));
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function figure(): BelongsTo
    {
        return $this->belongsTo(Figure::class);
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(FigureProfile::class, 'figure_profile_id');
    }

    public function recommendations(): HasMany
    {
        return $this->hasMany(PoseRecommendation::class)->orderBy('rank');
    }

    public function generatedImages(): HasMany
    {
        return $this->hasMany(GeneratedImage::class);
    }
}

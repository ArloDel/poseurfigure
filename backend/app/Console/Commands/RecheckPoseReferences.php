<?php

namespace App\Console\Commands;

use App\Models\PoseReference;
use App\Services\AIService;
use App\Services\ReferenceService;
use Illuminate\Console\Command;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Storage;

/**
 * Reads the accepted Pinterest references again with the AI service's current rules (for example after the
 * figure-photo check was added) and rejects the ones that no longer pass, deleting their stored image.
 */
class RecheckPoseReferences extends Command
{
    protected $signature = 'figurepose:recheck-references {--character= : only this character key, e.g. spiderman}';

    protected $description = 'Re-read accepted pose references and reject those the current rules turn down';

    public function handle(AIService $ai, ReferenceService $references): int
    {
        $query = PoseReference::accepted()->with('profile')->orderBy('id');
        if ($key = $this->option('character')) {
            $query->where('character_key', $key);
        }
        $refs = $query->get();
        $rejected = 0;
        $keys = [];

        foreach ($refs as $ref) {
            try {
                $read = $ai->readReference($ref->source_url, $ref->profile?->slug ?? 'humanoid_v1');
            } catch (RequestException $e) {
                $this->warn("#{$ref->id}: could not be read now ({$e->response->status()}), kept");

                continue;
            }
            if ($read['accepted'] ?? false) {
                $this->line("#{$ref->id}: kept");

                continue;
            }
            Storage::disk($ref->image_disk)->delete($ref->image_path);
            $ref->update(['status' => 'rejected', 'reject_reason' => substr((string) ($read['reason'] ?? 'unknown'), 0, 40),
                'image_disk' => null, 'image_path' => null]);
            $keys[$ref->character_key] = true;
            $rejected++;
            $this->line("#{$ref->id}: rejected ({$read['reason']})");
        }

        foreach (array_keys($keys) as $key) {
            $found = PoseReference::accepted()->where('character_key', $key)->count();
            \App\Models\ReferenceSearch::where('character_key', $key)->update(['found' => $found]);
            $references->refreshAnalyses($key);
        }
        $this->info("Checked {$refs->count()}, rejected {$rejected}.");

        return self::SUCCESS;
    }
}

<?php

namespace Database\Seeders;

use App\Models\FigureProfile;
use Illuminate\Database\Seeder;
use RuntimeException;

class FigureProfileSeeder extends Seeder
{
    /** Loads every skeleton profile JSON so new profiles need configuration, not code (FIG-05). */
    public function run(): void
    {
        $dir = config('figurepose.skeleton_profiles_path');
        $files = glob(rtrim($dir, '/\\').'/*.json') ?: [];

        if ($files === []) {
            throw new RuntimeException("No skeleton profiles found in [{$dir}]. Set SKELETON_PROFILES_PATH.");
        }

        foreach ($files as $file) {
            $config = json_decode((string) file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);

            FigureProfile::updateOrCreate(
                ['slug' => $config['profile']],
                [
                    'name' => $config['name'],
                    'category' => $config['category'],
                    'version' => $config['version'] ?? 1,
                    'skeleton_config' => $config,
                    'is_active' => true,
                ],
            );
        }
    }
}

<?php

namespace Database\Seeders;

use App\Models\FigureProfile;
use App\Models\PoseCatalog;
use Illuminate\Database\Seeder;

/**
 * A small starter catalog so the API and app have real data to show.
 * Joint positions are normalized (0-1) 2D keypoints; angles follow each profile's angle_convention.
 */
class PoseCatalogSeeder extends Seeder
{
    public function run(): void
    {
        $profiles = FigureProfile::pluck('id', 'category');
        $creditsFile = public_path('catalog/credits.json');
        $credits = is_file($creditsFile) ? json_decode((string) file_get_contents($creditsFile), true) : [];

        foreach ($this->poses() as $pose) {
            PoseCatalog::updateOrCreate(
                ['slug' => $pose['slug']],
                [
                    'figure_profile_id' => $profiles[$pose['profile']],
                    'name' => $pose['name'],
                    'category' => $pose['category'],
                    'difficulty' => $pose['difficulty'],
                    'description' => $pose['description'],
                    'joint_positions' => $pose['joints'],
                    'constraints' => $pose['constraints'] ?? null,
                    'instructions' => $pose['instructions'],
                    'reference_image' => "catalog/{$pose['slug']}.jpg",
                    'reference_credit' => $credits[$pose['slug']] ?? null,
                    'is_published' => true,
                ],
            );
        }
    }

    private function poses(): array
    {
        $stand = [
            'head' => [0.50, 0.12], 'neck' => [0.50, 0.21], 'chest' => [0.50, 0.30], 'waist' => [0.50, 0.44],
            'left_shoulder' => [0.40, 0.24], 'right_shoulder' => [0.60, 0.24],
            'left_elbow' => [0.36, 0.37], 'right_elbow' => [0.64, 0.37],
            'left_wrist' => [0.34, 0.50], 'right_wrist' => [0.66, 0.50],
            'left_hip' => [0.44, 0.49], 'right_hip' => [0.56, 0.49],
            'left_knee' => [0.43, 0.68], 'right_knee' => [0.57, 0.68],
            'left_ankle' => [0.42, 0.89], 'right_ankle' => [0.58, 0.89],
        ];
        $with = fn (array $changes) => array_merge($stand, $changes);

        return [
            [
                'slug' => 'rider-ready-stance', 'profile' => 'humanoid', 'name' => 'Rider ready stance',
                'category' => 'action', 'difficulty' => 'medium',
                'description' => 'A low, wide fighting stance. The lead fist guards the body, the rear hand rises open and ready.',
                'joints' => $with(['left_elbow' => [0.30, 0.37], 'left_wrist' => [0.20, 0.37], 'right_elbow' => [0.75, 0.30],
                    'right_wrist' => [0.80, 0.16], 'left_knee' => [0.21, 0.64], 'left_ankle' => [0.17, 0.84],
                    'right_knee' => [0.68, 0.74], 'right_ankle' => [0.88, 0.90]]),
                'constraints' => ['right_knee' => ['target' => 120, 'warn_above_profile_max' => true]],
                'instructions' => [
                    ['step' => 1, 'body_part' => 'torso', 'movement' => 'twist', 'target_angle' => 25, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'head', 'movement' => 'tilt_down', 'target_angle' => 10, 'priority' => 'low'],
                    ['step' => 3, 'body_part' => 'right_elbow', 'movement' => 'bend', 'target_angle' => 95, 'priority' => 'high'],
                    ['step' => 4, 'body_part' => 'left_wrist', 'movement' => 'open_and_raise', 'target_angle' => 40, 'priority' => 'medium'],
                    ['step' => 5, 'body_part' => 'left_shoulder', 'movement' => 'raise', 'target_angle' => 80, 'priority' => 'medium'],
                    ['step' => 6, 'body_part' => 'hips', 'movement' => 'spread', 'target_angle' => 40, 'priority' => 'high'],
                    ['step' => 7, 'body_part' => 'right_knee', 'movement' => 'bend', 'target_angle' => 120, 'priority' => 'high'],
                ],
            ],
            [
                'slug' => 'fencing-lunge', 'profile' => 'humanoid', 'name' => 'Fencing lunge',
                'category' => 'cinematic', 'difficulty' => 'hard',
                'description' => 'A long forward lunge with the weapon arm fully extended.',
                'joints' => $with(['right_elbow' => [0.78, 0.26], 'right_wrist' => [0.95, 0.24], 'left_knee' => [0.30, 0.70],
                    'left_ankle' => [0.15, 0.88], 'right_knee' => [0.70, 0.66], 'right_ankle' => [0.74, 0.89]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'right_elbow', 'movement' => 'straighten', 'target_angle' => 175, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'right_knee', 'movement' => 'bend', 'target_angle' => 95, 'priority' => 'high'],
                    ['step' => 3, 'body_part' => 'left_knee', 'movement' => 'straighten', 'target_angle' => 170, 'priority' => 'medium'],
                ],
            ],
            [
                'slug' => 'shield-guard', 'profile' => 'humanoid', 'name' => 'Shield guard',
                'category' => 'display', 'difficulty' => 'easy',
                'description' => 'Shield raised across the chest, weight on the back foot.',
                'joints' => $with(['left_elbow' => [0.44, 0.34], 'left_wrist' => [0.56, 0.30]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'left_elbow', 'movement' => 'bend', 'target_angle' => 70, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'torso', 'movement' => 'lean_back', 'target_angle' => 10, 'priority' => 'low'],
                ],
            ],
            [
                'slug' => 'ledge-lookout', 'profile' => 'anime', 'name' => 'Ledge lookout',
                'category' => 'calm', 'difficulty' => 'easy',
                'description' => 'Standing on a ledge, cape back, eyes on the horizon.',
                'joints' => $with(['head' => [0.54, 0.12]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'head', 'movement' => 'turn', 'target_angle' => 30, 'priority' => 'medium'],
                    ['step' => 2, 'body_part' => 'left_knee', 'movement' => 'bend', 'target_angle' => 160, 'priority' => 'low'],
                ],
            ],
            [
                'slug' => 'sword-draw', 'profile' => 'anime', 'name' => 'Sword draw',
                'category' => 'cinematic', 'difficulty' => 'hard',
                'description' => 'Both hands on the hilt at the hip, about to draw.',
                'joints' => $with(['left_wrist' => [0.46, 0.47], 'right_wrist' => [0.44, 0.46], 'left_knee' => [0.32, 0.67], 'right_knee' => [0.64, 0.67]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'right_elbow', 'movement' => 'bend', 'target_angle' => 85, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'left_elbow', 'movement' => 'bend', 'target_angle' => 100, 'priority' => 'high'],
                    ['step' => 3, 'body_part' => 'hips', 'movement' => 'spread', 'target_angle' => 35, 'priority' => 'medium'],
                ],
            ],
            [
                'slug' => 'commander-stance', 'profile' => 'mecha', 'name' => 'Commander stance',
                'category' => 'display', 'difficulty' => 'easy',
                'description' => 'Wide planted legs, one fist raised toward the camera.',
                'joints' => $with(['right_elbow' => [0.62, 0.30], 'right_wrist' => [0.45, 0.22], 'left_knee' => [0.30, 0.70], 'right_knee' => [0.70, 0.70]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'right_elbow', 'movement' => 'bend', 'target_angle' => 60, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'hips', 'movement' => 'spread', 'target_angle' => 45, 'priority' => 'high'],
                ],
            ],
            [
                'slug' => 'rifle-aim', 'profile' => 'mecha', 'name' => 'Rifle aim',
                'category' => 'cinematic', 'difficulty' => 'medium',
                'description' => 'Rifle shouldered and aimed past the camera. Check that shoulder armor clears the arm.',
                'joints' => $with(['right_elbow' => [0.70, 0.30], 'right_wrist' => [0.85, 0.27], 'left_elbow' => [0.55, 0.33], 'left_wrist' => [0.75, 0.30]]),
                'instructions' => [
                    ['step' => 1, 'body_part' => 'right_shoulder', 'movement' => 'raise', 'target_angle' => 85, 'priority' => 'high'],
                    ['step' => 2, 'body_part' => 'left_elbow', 'movement' => 'bend', 'target_angle' => 110, 'priority' => 'medium'],
                ],
            ],
        ];
    }
}

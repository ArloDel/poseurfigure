<?php

return [

    /*
    | Skeleton profile definitions shared with the AI service (repo: /shared/skeleton_profiles).
    */
    'skeleton_profiles_path' => env('SKELETON_PROFILES_PATH', base_path('../shared/skeleton_profiles')),

    /*
    | Where user photos are stored. Must be a private disk (PRD 15: private original-image storage).
    */
    'image_disk' => env('FIGUREPOSE_IMAGE_DISK', 's3'),

    'upload' => [
        'max_kb' => (int) env('UPLOAD_MAX_KB', 10240),          // 10 MB
        'min_dimension' => (int) env('UPLOAD_MIN_DIMENSION', 480),
        'max_dimension' => (int) env('UPLOAD_MAX_DIMENSION', 8000),
        'mimes' => ['jpeg', 'png', 'webp'],
    ],

    'ai_service' => [
        'url' => rtrim((string) env('AI_SERVICE_URL', 'http://localhost:8001'), '/'),
        'timeout' => (int) env('AI_SERVICE_TIMEOUT', 30),
    ],

    'analysis' => [
        'max_attempts' => (int) env('ANALYSIS_MAX_ATTEMPTS', 3),
        // Suggested client polling, returned with every in-progress status (PRD 11.4).
        'poll_after_seconds' => 2,
    ],
];

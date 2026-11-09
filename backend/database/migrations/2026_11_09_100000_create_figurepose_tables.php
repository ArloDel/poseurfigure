<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('figure_profiles', function (Blueprint $table) {
            $table->id();
            $table->string('slug')->unique();          // humanoid_v1, anime_v1, mecha_v1
            $table->string('name');
            $table->string('category');                // humanoid, anime, mecha, creature...
            $table->unsignedSmallInteger('version')->default(1);
            $table->json('skeleton_config');           // keypoints, connections, joint limits
            $table->boolean('is_active')->default(true);
            $table->timestamps();
        });

        Schema::create('figures', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('figure_profile_id')->constrained()->restrictOnDelete();
            $table->string('name');
            $table->string('brand')->nullable();
            $table->json('articulation_config')->nullable();
            $table->timestamps();
        });

        Schema::create('analyses', function (Blueprint $table) {
            $table->id();
            $table->uuid('public_id')->unique();
            // Either a signed-in user or a guest device (AUTH-05) owns an analysis.
            $table->foreignId('user_id')->nullable()->constrained()->cascadeOnDelete();
            $table->string('guest_key_hash', 64)->nullable()->index();
            $table->foreignId('figure_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('figure_profile_id')->nullable()->constrained()->nullOnDelete();
            $table->string('analysis_mode', 16);
            $table->string('status', 16)->default('pending')->index();
            $table->string('image_disk', 32);
            $table->string('image_path');
            $table->string('image_mime', 32);
            $table->unsignedInteger('image_size');
            $table->unsignedInteger('image_width');
            $table->unsignedInteger('image_height');
            $table->json('pose_data')->nullable();
            $table->json('quality')->nullable();
            $table->string('ai_model_version')->nullable();
            $table->string('failure_code', 48)->nullable();
            $table->string('failure_message')->nullable();
            $table->unsignedTinyInteger('attempts')->default(0);
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();

            $table->index('user_id');
        });

        Schema::create('pose_catalog', function (Blueprint $table) {
            $table->id();
            $table->foreignId('figure_profile_id')->constrained()->restrictOnDelete();
            $table->string('slug')->unique();
            $table->string('name');
            $table->string('category', 32);
            $table->string('difficulty', 16);
            $table->text('description')->nullable();
            $table->json('joint_positions');           // target keypoints, normalized 0-1
            $table->json('constraints')->nullable();   // feasibility metadata
            $table->json('instructions');              // structured, machine-readable steps
            $table->string('reference_image')->nullable();
            $table->json('reference_credit')->nullable();
            $table->boolean('is_published')->default(true);
            $table->timestamps();

            $table->index(['figure_profile_id', 'category'], 'idx_poses_profile_category');
        });

        Schema::create('pose_recommendations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('analysis_id')->constrained()->cascadeOnDelete();
            $table->foreignId('pose_catalog_id')->constrained('pose_catalog')->cascadeOnDelete();
            $table->unsignedTinyInteger('rank');
            $table->float('similarity_score');
            $table->float('feasibility_score');
            $table->timestamps();

            $table->index('analysis_id', 'idx_recommendations_analysis');
            $table->unique(['analysis_id', 'pose_catalog_id']);
        });

        Schema::create('generated_images', function (Blueprint $table) {
            $table->id();
            $table->foreignId('analysis_id')->constrained()->cascadeOnDelete();
            $table->foreignId('pose_catalog_id')->constrained('pose_catalog')->cascadeOnDelete();
            $table->string('image_path')->nullable();
            $table->string('provider')->nullable();
            $table->string('generation_status', 16)->default('pending');
            $table->string('validation_status', 16)->default('unvalidated');
            $table->string('idempotency_key', 64)->unique();
            $table->timestamps();
        });

        Schema::create('favorites', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('pose_catalog_id')->constrained('pose_catalog')->cascadeOnDelete();
            $table->timestamps();

            $table->unique(['user_id', 'pose_catalog_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('favorites');
        Schema::dropIfExists('generated_images');
        Schema::dropIfExists('pose_recommendations');
        Schema::dropIfExists('pose_catalog');
        Schema::dropIfExists('analyses');
        Schema::dropIfExists('figures');
        Schema::dropIfExists('figure_profiles');
    }
};

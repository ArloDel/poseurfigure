<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Pose references found on Pinterest for a character (personal instances only, see config/figurepose.php).
        // Rejected images are kept too, with the reason, so they are never downloaded again.
        Schema::create('pose_references', function (Blueprint $table) {
            $table->id();
            $table->string('character_key', 160)->index();
            $table->string('character_name', 160);
            $table->foreignId('figure_profile_id')->nullable()->constrained('figure_profiles')->nullOnDelete();
            $table->string('source', 20)->default('pinterest');
            $table->text('source_url');
            $table->char('source_url_hash', 64)->unique();
            $table->string('status', 20); // accepted | rejected
            $table->string('reject_reason', 40)->nullable();
            $table->string('image_disk', 40)->nullable();
            $table->string('image_path')->nullable();
            $table->unsignedInteger('image_width')->nullable();
            $table->unsignedInteger('image_height')->nullable();
            $table->json('joint_positions')->nullable();
            $table->json('figure_box')->nullable();
            $table->json('appearance')->nullable();
            $table->timestamps();
        });

        // One search per character: its progress, so the app can say "Finding poses... 6/20".
        Schema::create('reference_searches', function (Blueprint $table) {
            $table->id();
            $table->string('character_key', 160)->unique();
            $table->string('character_name', 160);
            $table->foreignId('figure_profile_id')->nullable()->constrained('figure_profiles')->nullOnDelete();
            $table->string('status', 20); // running | done | failed
            $table->unsignedInteger('total')->default(0);
            $table->unsignedInteger('checked')->default(0);
            $table->unsignedInteger('found')->default(0);
            $table->string('error')->nullable();
            $table->timestamp('finished_at')->nullable();
            $table->timestamps();
        });

        // A recommendation is a catalog pose or a found reference.
        Schema::table('pose_recommendations', function (Blueprint $table) {
            $table->foreignId('pose_catalog_id')->nullable()->change();
            $table->foreignId('pose_reference_id')->nullable()->after('pose_catalog_id')
                ->constrained('pose_references')->cascadeOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('pose_recommendations', function (Blueprint $table) {
            $table->dropConstrainedForeignId('pose_reference_id');
        });
        Schema::dropIfExists('reference_searches');
        Schema::dropIfExists('pose_references');
    }
};

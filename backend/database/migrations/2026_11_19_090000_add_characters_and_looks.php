<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Pose ideas: the same character first, then figures that look alike.
        Schema::table('pose_catalog', function (Blueprint $table) {
            $table->string('character_name', 160)->nullable()->after('description');
            $table->string('character_variant', 160)->nullable()->after('character_name');
            $table->string('franchise', 160)->nullable()->after('character_variant');
            // SigLIP 2 image embedding of the catalog figure (shared/catalog/appearance.json).
            $table->json('appearance')->nullable()->after('franchise');
        });

        Schema::table('analyses', function (Blueprint $table) {
            // The character the figure shows: suggested by the vision model ("ai") or typed by the user ("user").
            $table->string('character_name', 160)->nullable()->after('figure_profile_id');
            $table->string('character_source', 20)->nullable()->after('character_name');
            $table->json('character_details')->nullable()->after('character_source');
        });
    }

    public function down(): void
    {
        Schema::table('pose_catalog', function (Blueprint $table) {
            $table->dropColumn(['character_name', 'character_variant', 'franchise', 'appearance']);
        });
        Schema::table('analyses', function (Blueprint $table) {
            $table->dropColumn(['character_name', 'character_source', 'character_details']);
        });
    }
};

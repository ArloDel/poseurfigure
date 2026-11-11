<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pose_recommendations', function (Blueprint $table) {
            // Ranking score, similarity components, mirrored flag and joint-limit warnings from the matcher.
            $table->float('score')->nullable()->after('feasibility_score');
            $table->json('details')->nullable()->after('score');
        });
    }

    public function down(): void
    {
        Schema::table('pose_recommendations', function (Blueprint $table) {
            $table->dropColumn(['score', 'details']);
        });
    }
};

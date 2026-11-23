<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // A favorite is a catalog pose or a Pinterest reference.
        Schema::table('favorites', function (Blueprint $table) {
            $table->foreignId('pose_catalog_id')->nullable()->change();
            $table->foreignId('pose_reference_id')->nullable()->after('pose_catalog_id')
                ->constrained('pose_references')->cascadeOnDelete();
            $table->unique(['user_id', 'pose_reference_id']);
        });
    }

    public function down(): void
    {
        Schema::table('favorites', function (Blueprint $table) {
            $table->dropUnique(['user_id', 'pose_reference_id']);
            $table->dropConstrainedForeignId('pose_reference_id');
        });
    }
};

<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('generated_images', function (Blueprint $table) {
            $table->string('image_disk', 32)->nullable()->after('pose_catalog_id');
            $table->boolean('mirrored')->default(false)->after('validation_status');
            // Validation result (similarity, worst joint, reason) and the prompt sent to the provider.
            $table->json('details')->nullable()->after('mirrored');
            $table->string('failure_message')->nullable()->after('details');
            // When the user agreed to send their photo to the image service (PRD 15.1).
            $table->timestamp('consented_at')->nullable()->after('failure_message');
        });
    }

    public function down(): void
    {
        Schema::table('generated_images', function (Blueprint $table) {
            $table->dropColumn(['image_disk', 'mirrored', 'details', 'failure_message', 'consented_at']);
        });
    }
};

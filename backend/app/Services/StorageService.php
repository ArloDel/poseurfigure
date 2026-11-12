<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use RuntimeException;

class StorageService
{
    /** @return array{disk: string, path: string} */
    public function storeUserImage(UploadedFile $image, string $publicId): array
    {
        $disk = config('figurepose.image_disk');
        $ext = $image->extension() ?: 'jpg';
        $path = $image->storeAs('analyses/'.now()->format('Y/m'), "{$publicId}.{$ext}", [
            'disk' => $disk,
            'visibility' => 'private',
        ]);

        if ($path === false) {
            throw new RuntimeException('Could not store the uploaded photo.');
        }

        return ['disk' => $disk, 'path' => $path];
    }

    /** @return array{disk: string, path: string} */
    public function storeGenerated(string $bytes, string $name): array
    {
        $disk = config('figurepose.image_disk');
        $path = 'generated/'.now()->format('Y/m')."/{$name}.jpg";

        if (! Storage::disk($disk)->put($path, $bytes, ['visibility' => 'private'])) {
            throw new RuntimeException('Could not store the generated image.');
        }

        return ['disk' => $disk, 'path' => $path];
    }

    public function read(string $disk, string $path): string
    {
        $contents = Storage::disk($disk)->get($path);

        if ($contents === null) {
            throw new RuntimeException("Stored photo [{$path}] is missing.");
        }

        return $contents;
    }

    public function delete(string $disk, string $path): void
    {
        Storage::disk($disk)->delete($path);
    }
}

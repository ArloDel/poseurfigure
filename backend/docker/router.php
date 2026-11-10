<?php

/*
| Router for the PHP built-in dev server (see Dockerfile CMD; runs from public/).
|
| The built-in server serves files in public/ itself, without Laravel's CORS middleware.
| Flutter web loads images with fetch(), so catalog photos need a CORS header or they
| fail to load in the browser build. Everything else goes to Laravel's own router.
| In production nginx (or a CDN) serves /catalog with the same header.
*/

$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');
$public = getcwd();
$file = realpath($public.$path);

if (str_starts_with($path, '/catalog/') && $file !== false && str_starts_with($file, realpath($public.'/catalog').DIRECTORY_SEPARATOR) && is_file($file)) {
    $types = ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp', 'json' => 'application/json'];
    header('Content-Type: '.($types[strtolower(pathinfo($file, PATHINFO_EXTENSION))] ?? 'application/octet-stream'));
    header('Content-Length: '.filesize($file));
    header('Access-Control-Allow-Origin: *');
    header('Cache-Control: public, max-age=86400');
    readfile($file);

    return true;
}

return require dirname($public).'/vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php';

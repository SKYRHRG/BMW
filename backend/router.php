<?php
// Development/CI router for PHP's built-in web server. Production: Apache .htaccess.
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if (preg_match('~/(?:api/app/fauth/license/check|api/v1/license/validate|health)/?$~', $path)) {
    require __DIR__ . '/api.php';
    return true;
}
if (preg_match('~(?:^|/)(?:app|storage|tests)/~', $path)) {
    http_response_code(403); return true;
}
if (is_file(__DIR__.$path) && str_ends_with($path,'.php')) {
    if (basename($path) === 'install.php' || basename($path) === 'admin.php') {
        require __DIR__ . $path; return true;
    }
    http_response_code(403); return true;
}
if ($path === '/') {require __DIR__ . '/admin.php';return true;}
http_response_code(404);return true;

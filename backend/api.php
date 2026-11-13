<?php
declare(strict_types=1);
require_once __DIR__ . '/app/license.php';

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$path = rtrim($path, '/') ?: '/';
$isHealth = preg_match('~(?:^|/)health$~D', $path) === 1;
$isLicense = preg_match('~(?:^|/)(?:api/app/fauth/license/check|api/v1/license/validate)$~D', $path) === 1;
if (!$isHealth && !$isLicense) bmw_json(404, ['success'=>false,'message'=>'Not found.']);
if ($isHealth) {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') bmw_json(405,['success'=>false,'message'=>'Method not allowed.']);
    bmw_json(200, ['ok'=>true,'service'=>'BMW license server']);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') bmw_json(405,['success'=>false,'message'=>'Method not allowed.']);
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 8192) bmw_json(413,['success'=>false,'message'=>'Request too large.']);
try {
    $db = bmw_database();
    if (!bmw_rate_limit($db, (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown'))) {
        bmw_json(429, ['success'=>false,'message'=>'Too many attempts. Please try later.']);
    }
    $body = file_get_contents('php://input', false, null, 0, 8193);
    if ($body === false || strlen($body) > 8192) bmw_json(413,['success'=>false,'message'=>'Request too large.']);
    $request = json_decode($body, true);
    if (!is_array($request) || json_last_error() !== JSON_ERROR_NONE) {
        bmw_json(400,['success'=>false,'message'=>'Invalid JSON body.']);
    }
    $key = $request['Key'] ?? $request['licenseKey'] ?? '';
    $machine = $request['Machine'] ?? $request['deviceId'] ?? '';
    if (!is_string($key) || !is_string($machine)) {
        bmw_json(400,['success'=>false,'message'=>'Invalid request fields.']);
    }
    [$status, $result] = bmw_validate_license($db,$key,$machine);
    bmw_json($status,$result);
} catch (Throwable $e) {
    error_log('BMW API: '.get_class($e).' '.$e->getMessage());
    bmw_json(503, ['success'=>false,'message'=>'License service temporarily unavailable.']);
}

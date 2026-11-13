<?php
declare(strict_types=1);
date_default_timezone_set('UTC');

function bmw_config(): array {
    $configPath = dirname(__DIR__) . '/storage/config.php';
    if (is_file($configPath)) {
        $c = require $configPath;
        if (!is_array($c)) throw new RuntimeException('Invalid server config');
        return $c;
    }
    $host = getenv('BMW_DB_HOST');
    if ($host !== false && $host !== '') {
        return [
          'db_host'=>$host,
          'db_port'=>(int)(getenv('BMW_DB_PORT') ?: '3306'),
          'db_name'=>(string)getenv('BMW_DB_NAME'),
          'db_user'=>(string)getenv('BMW_DB_USER'),
          'db_pass'=>(string)getenv('BMW_DB_PASS'),
        ];
    }
    throw new RuntimeException('Server is not installed');
}
function bmw_database(): PDO {
    $c = bmw_config();
    $dbName = (string)($c['db_name'] ?? '');
    if (!preg_match('/^[a-zA-Z0-9_]{1,64}$/', $dbName)) {
        throw new RuntimeException('Invalid database configuration');
    }
    $port = (int)($c['db_port'] ?? 3306);
    $dsn = 'mysql:host=' . $c['db_host'] . ';port=' . $port . ';dbname=' . $dbName . ';charset=utf8mb4';
    return new PDO($dsn, $c['db_user'], $c['db_pass'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
        PDO::ATTR_TIMEOUT => 5
    ]);
}
function bmw_json(int $code, array $data): never {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
function bmw_h(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function bmw_session(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    session_name('BMW_ADMIN');
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_set_cookie_params([
        'lifetime'=>0, 'path'=>'/', 'secure'=> !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
        'httponly'=>true, 'samesite'=>'Strict'
    ]);
    session_start();
}
function bmw_csrf(): string {
    bmw_session();
    if (!isset($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(24));
    return (string)$_SESSION['csrf'];
}
function bmw_assert_csrf(): void {
    $token = (string)($_POST['csrf'] ?? '');
    if ($token === '' || !hash_equals(bmw_csrf(), $token)) {
        http_response_code(403); exit('Invalid CSRF token');
    }
}
function bmw_event(PDO $db, ?int $licenseId, string $type, string $details=''): void {
    $stmt = $db->prepare('INSERT INTO audit_events (license_id, event_type, details) VALUES (?,?,?)');
    $stmt->execute([$licenseId, substr($type,0,60), substr($details,0,500)]);
}
function bmw_rate_limit(PDO $db, string $clientIp, string $prefix='api', int $limit=40): bool {
    $hash = hash('sha256', $prefix . '|' . $clientIp);
    $check = $db->prepare('SELECT COUNT(*) FROM request_attempts WHERE client_hash = ? AND occurred_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 60 SECOND)');
    $check->execute([$hash]);
    if ((int)$check->fetchColumn() >= $limit) return false;
    $db->prepare('INSERT INTO request_attempts (client_hash) VALUES (?)')->execute([$hash]);
    if (random_int(1,200) === 1) $db->exec('DELETE FROM request_attempts WHERE occurred_at < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 2 DAY)');
    return true;
}

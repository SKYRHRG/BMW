<?php
declare(strict_types=1);
require_once __DIR__ . '/app/bootstrap.php';
$installed = is_file(__DIR__ . '/storage/config.php');
if ($installed) { http_response_code(403); exit('Installer disabled: backend is already installed.'); }
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    bmw_assert_csrf();
    $host = trim((string)($_POST['host'] ?? 'localhost'));
    $port = (int)($_POST['port'] ?? 3306);
    $name = trim((string)($_POST['dbname'] ?? ''));
    $user = trim((string)($_POST['dbuser'] ?? ''));
    $pass = (string)($_POST['dbpass'] ?? '');
    $email = strtolower(trim((string)($_POST['email'] ?? '')));
    $adminPassword = (string)($_POST['admin_password'] ?? '');
    try {
        if (!preg_match('/^[A-Za-z0-9_.-]{1,200}$/D', $host) ||
            $port < 1 || $port > 65535 ||
            !preg_match('/^[A-Za-z0-9_]{1,64}$/D', $name) ||
            $user === '' || $user !== trim($user) ||
            !filter_var($email, FILTER_VALIDATE_EMAIL) ||
            strlen($adminPassword) < 12) {
            throw new RuntimeException('Check database details, email, and admin password (minimum 12 characters).');
        }
        if (!extension_loaded('pdo_mysql')) {
            throw new RuntimeException('Your host needs the pdo_mysql PHP extension.');
        }
        $db = new PDO("mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4",
            $user,$pass,[
                PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES=>false
            ]);
        $schema = file_get_contents(__DIR__ . '/schema.mysql.sql');
        if ($schema === false) throw new RuntimeException('Missing SQL schema');
        // All schema statements are SQL DDL without stored procedures/semicolons in strings.
        foreach (explode(';', preg_replace('/^--.*$/m', '', $schema)) as $statement) {
            if (trim($statement) !== '') $db->exec($statement);
        }
        $count = (int)$db->query('SELECT COUNT(*) FROM admins')->fetchColumn();
        if ($count > 0) throw new RuntimeException('Existing admin found in database: refusing to replace access.');
        $db->prepare('INSERT INTO admins (email,password_hash) VALUES (?,?)')
           ->execute([$email,password_hash($adminPassword,PASSWORD_DEFAULT)]);
        $config = "<?php\nreturn " . var_export([
            'db_host'=>$host,'db_port'=>$port,
            'db_name'=>$name,'db_user'=>$user,'db_pass'=>$pass
        ], true) . ";\n";
        $storage = __DIR__ . '/storage';
        if (!is_dir($storage) && !mkdir($storage,0700,true) && !is_dir($storage)) {
            throw new RuntimeException('Cannot create storage directory');
        }
        $path = $storage . '/config.php';
        $created = fopen($path,'x');
        if ($created === false) throw new RuntimeException('Cannot write config; ensure storage is writable, and installer is not already complete.');
        @chmod($path,0600);
        fwrite($created,$config);
        fclose($created);
        session_regenerate_id(true);
        $_SESSION = [];
        header('Location: admin.php?installed=1',true,303);
        exit;
    } catch (Throwable $e) {
        $error = $e->getMessage();
        error_log('BMW installer: '.get_class($e).' '.$error);
    }
}
bmw_session();
$token = bmw_csrf();
?>
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BMW License Server Installer</title>
<style>
body{background:#eef2f6;font:16px system-ui,sans-serif;color:#203047;margin:0}
main{max-width:550px;background:white;margin:5vh auto;padding:30px;border-radius:14px;box-shadow:0 8px 30px #0001}
h1{margin-top:0} label{display:block;margin:16px 0 6px;font-weight:600}
input{box-sizing:border-box;width:100%;padding:11px;border:1px solid #bac6d6;border-radius:8px;font:inherit}
button{width:100%;margin-top:22px;padding:12px;border:0;border-radius:8px;background:#1766a8;color:white;font-size:17px;cursor:pointer}
.error{padding:10px;background:#fce9e9;color:#970e0e;border-radius:8px}
small{color:#566878}
</style></head><body><main>
<h1>BMW License Server</h1><p>One-time PHP + MySQL setup</p>
<?php if (isset($error)): ?><p class="error"><?= bmw_h($error) ?></p><?php endif; ?>
<form method="post" autocomplete="off">
<input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<label>MySQL Host</label><input name="host" value="localhost" required>
<label>MySQL Port</label><input type="number" name="port" value="3306" min="1" max="65535" required>
<label>Database Name</label><input name="dbname" required pattern="[A-Za-z0-9_]+">
<label>Database Username</label><input name="dbuser" required>
<label>Database Password</label><input type="password" name="dbpass" autocomplete="new-password">
<label>Administrator Email</label><input type="email" name="email" required>
<label>Administrator Password</label><input type="password" name="admin_password" minlength="12" autocomplete="new-password" required>
<small>Use HTTPS on your hosting account. The installer disables itself after writing the config.</small>
<button type="submit">Install BMW License Server</button></form>
</main></body></html>

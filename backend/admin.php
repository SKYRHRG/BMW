<?php
declare(strict_types=1);
require_once __DIR__ . '/app/bootstrap.php';

bmw_session();
header('X-Content-Type-Options: nosniff');
header('Cache-Control: private, no-store');
$notice = '';
$error = '';
try {
    $db = bmw_database();
} catch (Throwable $e) {
    http_response_code(503);
    echo '<!doctype html><meta charset="utf-8"><title>BMW Setup</title><p>BMW License Server is not installed or database is unavailable.</p><p><a href="install.php">Open installer</a></p>';
    exit;
}

function bmw_redirect(string $msg = 'Saved'): never {
    header('Location: admin.php?notice=' . rawurlencode($msg), true, 303);
    exit;
}
function bmw_admin_logged_in(): bool {
    return isset($_SESSION['admin_id']) && is_int($_SESSION['admin_id']);
}
function bmw_generated_license(): string {
    $raw = strtoupper(bin2hex(random_bytes(16)));
    return 'BMW-' . implode('-', str_split($raw, 4));
}
function bmw_key_hash(string $key): string {
    return hash('sha256', strtoupper(trim($key)));
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    bmw_assert_csrf();
    $action = (string)($_POST['action'] ?? '');
    if ($action === 'login' && !bmw_admin_logged_in()) {
        $ip = (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown');
        try {
            if (!bmw_rate_limit($db,$ip,'admin-login',8)) {
                $error = 'Too many attempts. Try again later.';
            } else {
                $email = strtolower(trim((string)($_POST['email'] ?? '')));
                $query = $db->prepare('SELECT id,password_hash FROM admins WHERE email=? LIMIT 1');
                $query->execute([$email]);
                $admin = $query->fetch();
                $pw = (string)($_POST['password'] ?? '');
                if ($admin && password_verify($pw,$admin['password_hash'])) {
                    session_regenerate_id(true);
                    $_SESSION['admin_id'] = (int)$admin['id'];
                    $_SESSION['csrf'] = bin2hex(random_bytes(24));
                    bmw_redirect('Logged in');
                }
                $error = 'Invalid credentials.';
            }
        } catch (Throwable $e) {
            error_log('BMW admin login: '.$e->getMessage());
            $error = 'Cannot sign in. Try again.';
        }
    } elseif ($action === 'logout' && bmw_admin_logged_in()) {
        $_SESSION = [];
        session_regenerate_id(true);
        bmw_redirect('Logged out');
    } elseif (bmw_admin_logged_in()) {
        try {
            if ($action === 'create') {
                $key = strtoupper(trim((string)($_POST['license_key'] ?? '')));
                if ($key === '') $key = bmw_generated_license();
                if (!preg_match('/^[A-Z0-9-]{8,128}$/D', $key)) throw new RuntimeException('Invalid license key format.');
                $days = filter_var($_POST['days'] ?? 30, FILTER_VALIDATE_INT);
                $seats = filter_var($_POST['max_devices'] ?? 1, FILTER_VALIDATE_INT);
                if ($days === false || $days < 1 || $days > 3650 ||
                    $seats === false || $seats < 1 || $seats > 100)
                    throw new RuntimeException('Invalid expiry days or device limit.');
                $plan = trim((string)($_POST['plan'] ?? 'standard'));
                $label = trim((string)($_POST['label'] ?? ''));
                if ($plan === '' || strlen($plan) > 64 || strlen($label) > 190)
                    throw new RuntimeException('Invalid plan or label.');
                $stmt = $db->prepare("INSERT INTO licenses
                    (key_hash,key_hint,label,plan,status,starts_at,expires_at,max_devices)
                    VALUES (?,?,?,?, 'active',UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL ? DAY),?)");
                $stmt->execute([bmw_key_hash($key), substr($key,0,8), $label,$plan,$days,$seats]);
                bmw_event($db,(int)$db->lastInsertId(),'create','License created');
                $_SESSION['one_time_key'] = $key;
                bmw_redirect('New license created');
            }
            $id = filter_var($_POST['license_id'] ?? null, FILTER_VALIDATE_INT);
            if ($id === false || !$id || $id < 1) throw new RuntimeException('Select a license.');
            if ($action === 'status') {
                $status = (string)($_POST['status'] ?? '');
                if (!in_array($status,['active','suspended','revoked'],true)) throw new RuntimeException('Invalid status.');
                $query = $db->prepare('UPDATE licenses SET status=? WHERE id=?');
                $query->execute([$status,$id]);
                bmw_event($db,$id,'status','Set to '.$status);
                bmw_redirect('License status updated');
            }
            if ($action === 'renew') {
                $days = filter_var($_POST['days'] ?? 30, FILTER_VALIDATE_INT);
                if ($days === false || $days < 1 || $days > 3650) throw new RuntimeException('Invalid renewal period.');
                $query = $db->prepare("UPDATE licenses SET expires_at=DATE_ADD(GREATEST(expires_at,UTC_TIMESTAMP()), INTERVAL ? DAY) WHERE id=?");
                $query->execute([$days,$id]);
                bmw_event($db,$id,'renew','Extended by '.$days.' days');
                bmw_redirect('License extended');
            }
            if ($action === 'reset_devices') {
                $query = $db->prepare('DELETE FROM devices WHERE license_id=?');
                $query->execute([$id]);
                bmw_event($db,$id,'reset_devices','All device bindings cleared');
                bmw_redirect('Device bindings reset');
            }
            if ($action === 'device_limit') {
                $limit = filter_var($_POST['max_devices'] ?? null, FILTER_VALIDATE_INT);
                if ($limit === false || $limit < 1 || $limit > 100) throw new RuntimeException('Device limit must be 1 to 100.');
                $query = $db->prepare('UPDATE licenses SET max_devices=? WHERE id=?');
                $query->execute([$limit,$id]);
                bmw_event($db,$id,'device_limit','Limit updated');
                bmw_redirect('Device limit updated');
            }
            throw new RuntimeException('Unknown action.');
        } catch (Throwable $e) {
            if ($e instanceof PDOException && $e->getCode() === '23000') {
                $error = 'License already exists.';
            } else {
                error_log('BMW admin action: '.get_class($e).': '.$e->getMessage());
                $error = $e instanceof RuntimeException ? $e->getMessage() : 'Database action failed.';
            }
        }
    } else {
        $error = 'Sign in required.';
    }
}
$token = bmw_csrf();
$loggedIn = bmw_admin_logged_in();
$notice = (string)($_GET['notice'] ?? '');
if ($loggedIn) {
    $counts = $db->query("SELECT
        COUNT(*) AS total,
        SUM(status='active') AS active_count,
        SUM(status='revoked') AS revoked_count,
        SUM(expires_at<UTC_TIMESTAMP()) AS expired_count FROM licenses")->fetch();
    $rows = $db->query("SELECT l.id,l.key_hint,l.label,l.plan,l.status,l.starts_at,l.expires_at,
        l.max_devices,l.created_at, COUNT(d.id) AS used_devices
        FROM licenses l LEFT JOIN devices d ON d.license_id=l.id
        GROUP BY l.id,l.key_hint,l.label,l.plan,l.status,l.starts_at,l.expires_at,l.max_devices,l.created_at
        ORDER BY l.id DESC LIMIT 100")->fetchAll();
    $audit = $db->query('SELECT event_type,details,created_at FROM audit_events ORDER BY id DESC LIMIT 25')->fetchAll();
}
$keyCreated = $loggedIn ? (string)($_SESSION['one_time_key'] ?? '') : '';
unset($_SESSION['one_time_key']);
?>
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BMW License Management</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6/css/all.min.css">
<style>body{background:#f4f6f9}.wrapper{max-width:1300px;margin:auto;padding:24px}
.card{border-radius:9px}.table th,.table td{vertical-align:middle}
label{font-weight:600;font-size:14px}.inline-form{display:inline-flex;gap:5px;align-items:center;margin:3px}
.inline-form input,.inline-form select{width:auto;max-width:95px}code{white-space:normal;overflow-wrap:anywhere}
</style></head><body><div class="wrapper">
<div class="d-flex justify-content-between align-items-center mb-4">
<h1 class="h3"><i class="fas fa-shield-alt text-primary"></i> BMW License Server</h1>
<?php if ($loggedIn): ?><form method="post"><input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<input type="hidden" name="action" value="logout"><button class="btn btn-outline-secondary" type="submit">Sign out</button></form><?php endif; ?>
</div>
<?php if ($notice): ?><div class="alert alert-info"><?= bmw_h($notice) ?></div><?php endif; ?>
<?php if ($error): ?><div class="alert alert-danger"><?= bmw_h($error) ?></div><?php endif; ?>
<?php if (!$loggedIn): ?>
<div class="card mx-auto" style="max-width:450px"><div class="card-header"><b>Administrator Login</b></div>
<div class="card-body"><form method="post"><input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<input type="hidden" name="action" value="login">
<div class="form-group"><label>Email</label><input class="form-control" type="email" name="email" required></div>
<div class="form-group"><label>Password</label><input class="form-control" type="password" name="password" required></div>
<button type="submit" class="btn btn-primary btn-block">Sign in</button></form></div></div>
<?php else: ?>
<?php if ($keyCreated): ?>
<div class="alert alert-success"><b>New license key (copy now — shown only once):</b>
<code class="d-block text-dark mt-2"><?= bmw_h($keyCreated) ?></code></div>
<?php endif; ?>
<div class="row">
<div class="col-sm-6 col-md-3"><div class="small-box bg-info"><div class="inner"><h3><?= (int)($counts['total'] ?? 0) ?></h3><p>Total Licenses</p></div></div></div>
<div class="col-sm-6 col-md-3"><div class="small-box bg-success"><div class="inner"><h3><?= (int)($counts['active_count'] ?? 0) ?></h3><p>Active Status</p></div></div></div>
<div class="col-sm-6 col-md-3"><div class="small-box bg-danger"><div class="inner"><h3><?= (int)($counts['revoked_count'] ?? 0) ?></h3><p>Revoked</p></div></div></div>
<div class="col-sm-6 col-md-3"><div class="small-box bg-warning"><div class="inner"><h3><?= (int)($counts['expired_count'] ?? 0) ?></h3><p>Expired</p></div></div></div>
</div>
<div class="card"><div class="card-header"><b>Create / Import License</b></div>
<div class="card-body"><form method="post" class="row">
<input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<input type="hidden" name="action" value="create">
<div class="form-group col-md-4"><label>Existing key (optional — blank generates new)</label>
<input class="form-control" name="license_key" autocomplete="off" placeholder="BMW-..."></div>
<div class="form-group col-md-3"><label>Customer label</label><input class="form-control" name="label" maxlength="190"></div>
<div class="form-group col-md-2"><label>Plan</label><input class="form-control" name="plan" value="standard" maxlength="64"></div>
<div class="form-group col-md-1"><label>Days</label><input class="form-control" name="days" type="number" min="1" max="3650" value="30"></div>
<div class="form-group col-md-1"><label>Devices</label><input class="form-control" name="max_devices" type="number" min="1" max="100" value="1"></div>
<div class="form-group col-md-1 d-flex align-items-end"><button class="btn btn-success btn-block">Create</button></div>
</form></div></div>
<div class="card"><div class="card-header"><b>Licenses — Latest 100</b></div><div class="card-body table-responsive">
<table class="table table-striped table-sm"><thead><tr><th>ID / Key</th><th>Label</th><th>Status</th><th>Expires (UTC)</th><th>Devices</th><th>Actions</th></tr></thead><tbody>
<?php foreach ($rows as $row): ?>
<tr>
<td><b>#<?= (int)$row['id'] ?></b><br><code><?= bmw_h((string)$row['key_hint']) ?>…</code></td>
<td><?= bmw_h((string)$row['label']) ?><br><small><?= bmw_h((string)$row['plan']) ?></small></td>
<td><?= bmw_h((string)$row['status']) ?></td>
<td><?= bmw_h((string)$row['expires_at']) ?></td>
<td><?= (int)$row['used_devices'] ?> / <?= (int)$row['max_devices'] ?></td>
<td>
<form class="inline-form" method="post">
<input type="hidden" name="csrf" value="<?= bmw_h($token) ?>"><input type="hidden" name="action" value="status">
<input type="hidden" name="license_id" value="<?= (int)$row['id'] ?>">
<select class="form-control form-control-sm" name="status">
<?php foreach (['active','suspended','revoked'] as $s): ?><option value="<?= $s ?>" <?= $s===$row['status']?'selected':'' ?>><?= $s ?></option><?php endforeach; ?>
</select><button class="btn btn-sm btn-outline-primary">Set</button></form>
<form class="inline-form" method="post"><input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<input type="hidden" name="action" value="renew"><input type="hidden" name="license_id" value="<?= (int)$row['id'] ?>">
<input class="form-control form-control-sm" type="number" name="days" value="30" min="1" max="3650">
<button class="btn btn-sm btn-outline-success">Renew</button></form>
<form class="inline-form" method="post"><input type="hidden" name="csrf" value="<?= bmw_h($token) ?>">
<input type="hidden" name="action" value="device_limit"><input type="hidden" name="license_id" value="<?= (int)$row['id'] ?>">
<input class="form-control form-control-sm" type="number" name="max_devices" value="<?= (int)$row['max_devices'] ?>" min="1" max="100">
<button class="btn btn-sm btn-outline-secondary">Seats</button></form>
<form class="inline-form" method="post" onsubmit="return confirm('Reset device bindings for this license?')">
<input type="hidden" name="csrf" value="<?= bmw_h($token) ?>"><input type="hidden" name="action" value="reset_devices">
<input type="hidden" name="license_id" value="<?= (int)$row['id'] ?>">
<button class="btn btn-sm btn-outline-danger">Reset devices</button></form>
</td></tr><?php endforeach; ?>
</tbody></table></div></div>
<div class="card"><div class="card-header"><b>Recent Audit Events</b></div><div class="card-body table-responsive">
<table class="table table-sm"><thead><tr><th>Time (UTC)</th><th>Event</th><th>Details</th></tr></thead><tbody>
<?php foreach ($audit as $entry): ?><tr><td><?= bmw_h((string)$entry['created_at']) ?></td>
<td><?= bmw_h((string)$entry['event_type']) ?></td><td><?= bmw_h((string)$entry['details']) ?></td></tr><?php endforeach; ?>
</tbody></table></div></div>
<?php endif; ?>
<p class="text-muted text-sm">BMW backend v2 · API uses authorized server-side verification. This admin interface does not modify the original Windows EXE.</p>
</div></body></html>

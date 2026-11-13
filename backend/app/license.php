<?php
declare(strict_types=1);
require_once __DIR__ . '/bootstrap.php';

/**
 * Validate a server-side license record and atomically bind a device.
 * Request Key/Machine and licenseKey/deviceId forms are handled in api.php.
 * No client-side validation bypass is performed.
 *
 * @return array{0:int,1:array<string,mixed>}
 */
function bmw_validate_license(PDO $db, string $key, string $machine): array {
    $key = strtoupper(trim($key));
    $machine = trim($machine);
    if (!preg_match('/^[A-Z0-9-]{8,128}$/D', $key) ||
        strlen($machine) < 4 || strlen($machine) > 256 ||
        preg_match('/[\x00-\x1f]/', $machine)) {
        return [400, ['success'=>false,'message'=>'Invalid license request.']];
    }
    $keyHash = hash('sha256', $key);
    $machineHash = hash('sha256', $machine);
    $db->beginTransaction();
    try {
        $q = $db->prepare('SELECT id, plan, status, starts_at, expires_at, max_devices, update_url FROM licenses WHERE key_hash=? FOR UPDATE');
        $q->execute([$keyHash]);
        $license = $q->fetch();
        if (!$license) {
            $db->rollBack();
            return [401, ['success'=>false, 'message'=>'Invalid license key.']];
        }
        $id = (int)$license['id'];
        if ($license['status'] !== 'active') {
            $db->rollBack();
            return [401, ['success'=>false,'message'=>'License is ' . $license['status'] . '.']];
        }
        $now = new DateTimeImmutable('now', new DateTimeZone('UTC'));
        $start = new DateTimeImmutable($license['starts_at'], new DateTimeZone('UTC'));
        $expiry = new DateTimeImmutable($license['expires_at'], new DateTimeZone('UTC'));
        if ($now < $start || $now >= $expiry) {
            $db->rollBack();
            return [401, ['success'=>false,'message'=>'License expired or not active.']];
        }
        $deviceCheck = $db->prepare('SELECT id FROM devices WHERE license_id=? AND machine_hash=? LIMIT 1');
        $deviceCheck->execute([$id,$machineHash]);
        $deviceId = $deviceCheck->fetchColumn();
        if ($deviceId) {
            $db->prepare('UPDATE devices SET last_seen_at=UTC_TIMESTAMP() WHERE id=?')->execute([(int)$deviceId]);
        } else {
            $count = $db->prepare('SELECT COUNT(*) FROM devices WHERE license_id=?');
            $count->execute([$id]);
            if ((int)$count->fetchColumn() >= (int)$license['max_devices']) {
                $db->rollBack();
                return [409, ['success'=>false,'message'=>'Device limit reached.']];
            }
            $db->prepare('INSERT INTO devices (license_id,machine_hash) VALUES (?,?)')->execute([$id,$machineHash]);
        }
        $remaining = max(0, (int)ceil(($expiry->getTimestamp() - $now->getTimestamp()) / 86400));
        $db->commit();
        return [200, [
            'success'=>true, 'leftDays'=>$remaining, 'message'=>'License OK.',
            'KeyType'=>$license['plan'], 'paid'=>true, 'UpdateURL'=>(string)$license['update_url']
        ]];
    } catch (Throwable $e) {
        if ($db->inTransaction()) $db->rollBack();
        throw $e;
    }
}

#!/usr/bin/env python3
"""Integration test of BMW PHP backend and MySQL. Uses synthetic credentials/keys.

Called from GitHub Actions after mysql service health check; runs PHP localhost.
No real BMW EXE or vendor server contacted.
"""
import contextlib
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = "http://127.0.0.1:18892"
KEY = "BMW-TEST-1234-5678-90AB-CDEF-5678-1234"
MAC1 = "SYNTHETIC-DEVICE-ALPHA"
MAC2 = "SYNTHETIC-DEVICE-BETA"
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def req(path, *, form=None, payload=None, method=None):
    data = None
    headers = {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(ROOT + path, data=data, method=method, headers=headers)
    try:
        with client.open(call, timeout=6) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def json_req(path, payload):
    status, body = req(path, payload=payload)
    return status, json.loads(body)


def csrf_from(html):
    result = re.search(r'name="csrf" value="([a-f0-9]+)"', html)
    assert result, "CSRF hidden input not found"
    return result.group(1)


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("PASS", msg)


with subprocess.Popen(
    ["php", "-S", "127.0.0.1:18892", "-t", str(HERE), str(HERE / "router.php")],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE
) as server:
    for i in range(50):
        try:
            status, _ = req("/health")
            if status == 200:
                break
        except Exception:
            time.sleep(0.15)
    else:
        raise RuntimeError("PHP server failed to start")

    status, page = req("/install.php")
    expect(status == 200, "Installer renders before setup")

    token = csrf_from(page)
    status, page = req("/install.php", form={
        "csrf": token,
        "host": "127.0.0.1",
        "port": "3306",
        "dbname": "bmw_test",
        "dbuser": "bmw_user",
        "dbpass": "test_password",
        "email": "test@example.invalid",
        "admin_password": "BMW-Test-Admin-Pass-2026"
    })
    expect(status == 200 and "Administrator Login" in page, "Installer creates schema and administrator")
    expect((HERE / "storage/config.php").is_file(), "Installer writes protected config")

    status, body = req("/install.php")
    expect(status == 403, "Installer disabled after successful setup")

    status, page = req("/admin.php")
    token = csrf_from(page)
    status, page = req("/admin.php", form={
        "csrf": token, "action": "login",
        "email": "test@example.invalid",
        "password": "BMW-Test-Admin-Pass-2026"
    })
    expect(status == 200 and "Create / Import License" in page, "Administrator login")

    token = csrf_from(page)
    status, page = req("/admin.php", form={
        "csrf": token,
        "action": "create",
        "license_key": KEY,
        "label": "GitHub CI test only",
        "days": "30",
        "max_devices": "1",
        "plan": "standard"
    })
    expect(status == 200 and "New license created" in page, "Create license through authenticated admin panel")

    status, body = json_req("/api/app/fauth/license/check", {"Key": KEY, "Machine": MAC1})
    expect(status == 200 and body.get("success") is True and body.get("leftDays", 0) >= 29,
           "Original /fauth POST activates first device")

    status, body = json_req("/api/app/fauth/license/check", {"Key": KEY, "Machine": MAC1})
    expect(status == 200 and body.get("success") is True, "Revalidation of same device")

    status, body = json_req("/api/app/fauth/license/check", {"Key": KEY, "Machine": MAC2})
    expect(status == 409 and body.get("success") is False, "Device limit enforced")

    status, body = json_req("/api/app/fauth/license/check", {"Key": "BMW-DOES-NOT-EXIST", "Machine": MAC1})
    expect(status == 401 and body.get("success") is False, "Unknown key rejected")

    status, body = json_req("/api/v1/license/validate", {"licenseKey": KEY, "deviceId": MAC1})
    expect(status == 200 and body.get("success") is True, "Alternate request-field names supported")

    token = csrf_from(page)
    status, page = req("/admin.php", form={
        "csrf": token, "action": "status", "license_id": "1", "status": "revoked"
    })
    expect(status == 200 and "License status updated" in page, "Admin revoke operation")

    status, body = json_req("/api/app/fauth/license/check", {"Key": KEY, "Machine": MAC1})
    expect(status == 401 and body.get("success") is False, "Revoked license rejected by server")

    print("ALL BMW BACKEND MYSQL INTEGRATION TESTS PASSED")
    server.terminate()

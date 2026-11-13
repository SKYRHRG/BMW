"""BMW license client — editable recovery reconstruction.

Reconstructed from *static* Python 3.11 bytecode of license_client.pyc,
not the original .py source. Does not bypass license validation. Successful
activation requires HTTP 200 with JSON {"success": true} from an
authorized server, and any higher-level application checks still apply.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

DEFAULT_TIMEOUT = 15
DEFAULT_LICENSE_URL = "https://iambts.in/api/app/fauth/license/check"


class LicenseError(Exception):
    """License request or response processing error."""


def _pick_msg(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for field in ("message", "error", "msg", "reason", "detail"):
            value = obj.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def resolve_license_url() -> str:
    """Choose the server explicitly, rather than modifying compiled bytecode.

    Integration with the existing compiled GUI is NOT established.
    Calling this from new or restored application source is required.
    """
    return (os.getenv("LICENSE_API_URL") or DEFAULT_LICENSE_URL).strip()


def check_license(
    api_url: str,
    license_key: str,
    device_id: str,
    timeout: int | float = DEFAULT_TIMEOUT,
    *,
    retries: int = 1,
    session: Any = None,
) -> tuple[bool, int | None, str, str, dict[str, Any]]:
    """Reconstructed five-element contract.

    The two payload variants, success check, response fields and special
    handling for HTTP 401/429 are recovered from bytecode. Retry count,
    default timeout and exception details are configurable implementation
    choices pending full source recovery.
    """
    url = str(api_url or "").strip()
    key = str(license_key or "").strip()
    machine = str(device_id or "").strip()
    if not key or not machine:
        return False, None, "", "licenseKey/deviceId missing.", {}
    if not url.startswith("https://") and not url.startswith("http://localhost") and not url.startswith("http://127.0.0.1"):
        return False, None, "", "License server URL must use HTTPS.", {}

    is_fauth = "/fauth" in url.lower()
    payload = {"Key": key, "Machine": machine} if is_fauth else {"licenseKey": key, "deviceId": machine}
    headers = {"Content-Type": "application/json"}
    send = session if session is not None else requests
    for attempt in range(max(1, retries)):
        try:
            response = send.post(url, json=payload, headers=headers, timeout=timeout)
            try:
                raw = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                raw = {}
            data = raw if isinstance(raw, dict) else {}
            status = response.status_code
            if status == 200:
                ok = data.get("success") is True
                left = data.get("leftDays")
                try:
                    days = int(left) if left is not None else None
                except (TypeError, ValueError, OverflowError):
                    days = None
                message = _pick_msg(data) or ("License OK." if ok else "Invalid license key.")
                mode = "UPSTREAM-VALID" if ok and is_fauth else (str(data.get("mode") or "") if not is_fauth else "")
                return ok, days, mode, message, data
            if status == 401:
                return False, None, "", _pick_msg(data) or "Invalid license key.", data
            if status == 429:
                return False, None, "", _pick_msg(data) or "Too many attempts. Please try later.", data
            return False, None, "", _pick_msg(data) or f"Server error ({status}). Try again.", data
        except requests.exceptions.Timeout:
            if attempt + 1 == max(1, retries):
                return False, None, "", "Server timeout. Please try again.", {}
            time.sleep(0.15)
        except requests.exceptions.RequestException:
            if attempt + 1 == max(1, retries):
                return False, None, "", "Cannot connect to license server.", {}
            time.sleep(0.15)
    return False, None, "", "Cannot connect to license server.", {}

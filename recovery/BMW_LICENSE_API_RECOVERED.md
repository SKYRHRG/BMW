# BMW License API — Recovered from Python 3.11 bytecode

Status: Static reconstruction from BMW.exe. This document does not claim a live server capture or successful EXE rebuild.

## Original endpoint
URL: https://iambts.in/api/app/fauth/license/check
HTTP method: POST
Header: Content-Type: application/json

Recovered from license_dialog.pyc (endpoint) and license_client.pyc (requests.post).

## Request body on original /fauth URL

The client tests whether lowercased endpoint URL contains /fauth.
When true, its outgoing JSON object is:

    {"Key": "USER-ENTERED-KEY", "Machine": "LOCAL-DEVICE-ID"}

For any URL without /fauth, it uses a different JSON object:

    {"licenseKey": "USER-ENTERED-KEY", "deviceId": "LOCAL-DEVICE-ID"}

This is an important compatibility difference when migrating the endpoint. Neither example contains a real license key.

## Response behavior recovered from check_license

- Accepts HTTP 200 with JSON field success being actual boolean true (not the string "true").
- Reads leftDays and attempts integer conversion; absent/unparseable becomes null.
- Extracts first nonempty text from message, error, msg, reason, detail.
- For valid responses on /fauth endpoint, reports internal mode UPSTREAM-VALID.
- Returns five items: (valid, left_days_or_none, mode, message, raw_json).
- Handles HTTP 401 as invalid key; HTTP 429 as too many attempts.
- Other unsuccessful HTTP statuses produce an error message.
- Contains retry, timeout, and request exception handling.

Synthetic VALID response example (not captured):

    {"success": true, "leftDays": 30, "message": "License OK.", "KeyType": "standard", "UpdateURL": ""}

Synthetic INVALID response example (not captured):

    {"success": false, "message": "Invalid license key."}

The code checks 200/401/429. Do not assume a GET route or additional endpoints: none was established by the recovered license_client function.

## Local UI and metadata

The recovered license_dialog.pyc uses PySide6 and QSettings. It includes these persisted settings:
- license/masked_key
- license/machine_id
- license/left_days
- license/app_version
- license/server_msg
- license/key_type
- license/paid
- license/update_url
- license/tokens
- license/fauth_raw

It also references KeyType and UpdateURL in server data. The exact optional nesting has not been fully verified.

## URL override caveat

The license_dialog bytecode includes the string LICENSE_API_URL and os.environ.get, but it is not yet proven that the compiled bmw_gui entry point honors that variable. It may supply an explicit URL. Do not claim URL migration succeeded based only on the string.

## Source recovery and limitations

BMW.exe is confirmed PyInstaller / Python 3.11 with a PYZ archive containing 1,020 entries. Extracted modules include license_client.pyc, license_dialog.pyc, and bmw_gui.pyc.

License client and dialog contain readable code objects and recoverable control flow. The bmw_gui.pyc entry point is PyArmor-protected (short executable stub and protected data). The complete original editable .py source has NOT been recovered.

No production endpoint was called, no license check was bypassed, and no newly patched Windows EXE has been built.

## Evidence and reproducibility

Branch: recovery/bmw-static-20261113
- recovery/bmw_static_report.py
- recovery/license_probe.py
- recovery/target_license_modules.py
- recovery/license_contract_trace.py
- .github/workflows/bmw-static-recovery.yml

The Actions job artifact BMW-static-recovery-inventory contains the extracted package metadata, module inventories, and focused license disassembly.

For a replacement PHP backend, implement the verified POST/JSON contract first, then test against a controlled BMW client. Signature requirements or other checks may exist outside license_client.pyc and must not be bypassed.

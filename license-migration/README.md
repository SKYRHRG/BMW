# BMW — License-only migration

**Your request:** Keep the existing BMW.exe and every existing business function intact. Change only licensing so authorized licenses can be checked against your own PHP server.

This folder does not include a patched EXE or license bypass.

## Established facts

The extracted `license_dialog.pyc` contains `LICENSE_API_URL` and default URL `https://iambts.in/api/app/fauth/license/check`.

The extracted `license_client.pyc` sends a POST with `Content-Type: application/json` and body:

```json
{"Key":"LICENSE-KEY","Machine":"DEVICE-ID"}
```

On HTTP 200 it considers success only when `success` is actual boolean `true`; it also reads `leftDays`.

A separate PHP/MySQL backend implementing this contract exists in the `recovery/bmw-step3-backend-v2` branch, and passed isolated server integration tests.

## Critical blocker

The top-level `bmw_gui.pyc` is PyArmor-protected. It has NOT been proven that it accepts `LICENSE_API_URL` from its environment or that it doesn't pass an explicit URL to the dialog. A successful API-only test is not proof the original BMW.exe will activate with the new server.

Use `run-bmw-license-env.cmd` only as a **non-invasive test**. Edit the placeholder URL for your own deployed backend. The original compiled exe will be launched without code changes.

In a *permitted test environment*, check the backend request logs for that invocation and compare the license prompt's error/result. A missing request to your backend means the environment-only approach did not work; do not claim success.

If the main app forces an old server URL, source access or an authorized new build from the original project is necessary to change only the license call; `pyarmor` prevents a reliable drop-in edit to protected `bmw_gui.pyc` through source-level changes.

**Do not** replace program logic, disable license checks, spoof TLS certificates, intercept vendor domains, or install a launcher that overrides security checks.

## Tested and untested

- Static extracted client URL and POST/JSON contract: CONFIRMED.
- PHP/MySQL backend server tests: PASSED in GitHub CI, isolated from BMW.exe.
- Original BMW.exe + new server validation: NOT TESTED.
- Full existing functionality after migration: NOT TESTED.
- Rebuilt working BMW.exe: NOT PRODUCED.

Original ZIP/EXE is kept unchanged.

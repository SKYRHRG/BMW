# BMW Full Source Recovery — Final Assessment (13 Nov 2026)

## Result

**A 100%-working replacement BMW.exe could not be produced from the recovered material.**
The original BMW application is PyArmor-protected, and full program logic is not available as an editable source tree. The user-requested "BMW Full Code" is **not** recoverable from this analysis without additional authorized original source/backup material.

### Evidence

Extracted BMW.exe via PyInstaller: Python 3.11, approximately 1,020 PYZ entries.

Static pycdc decompilation of six first-party candidates yielded:

| Module | Result |
|---|---|
| `license_client.pyc` | Syntax-valid decompiled Python; functional behavior not fully proven |
| `license_dialog.pyc` | Syntax-valid decompiled Python; functional behavior not fully proven |
| `bmw_gui.pyc` | Main GUI protected with PyArmor; application source unrecovered |
| `bmw.pyc` | Decompiler output invalid Python syntax |
| `device_id.pyc` | Decompiler output invalid Python syntax |
| `runtime_bmw_paths.pyc` | Decompiler output invalid Python syntax |

Other first-party modules are embedded in PYZ: `bmw_login_clicker`, `bmw_updater`, `erail_onefile`, `indian_rail_avl_client`, `journey_fill`, `login_flow`, `payment_flow`, `review_booking`, `success_uploader`, `train_search_client`, `train_search_qt`, `train_select`, `utils`, and others.

Their presence does not establish that they have been recovered in runnable source form.

### Working material now available

- Original BMW EXE and support files, on the original repository `main` branch (not modified).
- Extracted PyInstaller bytecode ZIP, from prior GitHub Action.
- Syntax-valid, but unverified, decompiler output for `license_client.py` and `license_dialog.py`.
- Earlier hand-reconstructed editable Python license client/dialog and unit tests, on the recovery branch.
- Independently built PHP/MySQL license server and AdminLTE admin panel with 13/13 verified integration checks, on `recovery/bmw-step3-backend-v2`.
- Script, logs, and source recovery report in GitHub Actions artifact `BMW-FIRST-PARTY-SOURCE-RECOVERY`.

### Required to produce a fully functioning EXE

1. Recover original unprotected `bmw_gui.py` and other first-party original code from your saved backups or Git history, or reimplement the unrecoverable core.
2. Verify the native `_internal/onnxruntime/out/BMW.pyd` application dependency, Python version, interfaces and DLL loading.
3. Restore original machine identity semantics from `device_id.pyc`, compare against historical identifiers.
4. Integrate authenticated license checks with an independently verified new backend endpoint. Keep all server-side license verification.
5. Build and test on Windows x64 with PyInstaller and the original runtime dependencies; validate all user-facing workflows.

**No existing executable has been modified or bypassed. No complete rebuilt Windows EXE exists.** A license-only demonstration cannot be represented as the complete original BMW.

### Links

Source assessment branch: https://github.com/SKYRHRG/BMW/tree/recovery/bmw-full-recovery-20261113

Recovery workflow: https://github.com/SKYRHRG/BMW/actions/runs/43480759626

Backend ZIP: https://github.com/SKYRHRG/BMW/actions/runs/43477443818/artifacts/14064081092

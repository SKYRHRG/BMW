#!/usr/bin/env python3
"""Read-only BMW.exe package / license-protocol inventory.

This tool NEVER executes BMW.exe, *.pyd or the app's Python code.
It scans bytes and disassembles marshal code objects only if already
extracted as Python 3.11 .pyc files.
"""
from __future__ import annotations
import dis
import hashlib
import importlib.util
import io
import json
import marshal
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "recovery-output"
OUT.mkdir(parents=True, exist_ok=True)
EXTRACTED = ROOT / "BMW.exe_extracted"
URL_RX = re.compile(r"(?i)(?:https?|wss?)://[A-Za-z0-9.-]+(?::[0-9]{2,5})?(?:/[A-Za-z0-9/_~.%+@=-]{0,130})?")
NEEDLE_RX = re.compile(r"(?i)licen[cs]|activat|validat|subscri|api[/_.-]|endpoint|server_url|server_host|renewal|heartbeat|fingerprint|machine_id")
ASCII_RX = re.compile(rb"[\x20-\x7e]{8,}")
KEYS = ["BMW.exe", "_internal/onnxruntime/out/BMW.pyd", "_internal/pyarmor_runtime_007955/pyarmor_runtime.pyd"]
files_to_scan = [ROOT / p for p in KEYS]
if EXTRACTED.exists():
    files_to_scan += list(EXTRACTED.rglob("*.pyc"))
    files_to_scan += list(EXTRACTED.rglob("*.py"))
    files_to_scan += list(EXTRACTED.rglob("*.pyd"))
    files_to_scan += list(EXTRACTED.rglob("*.json"))
results, urls, extracted_inventory = [], {}, []
for file in files_to_scan:
    if not file.is_file():
        continue
    relative = str(file.relative_to(ROOT))
    if relative.endswith(".env") or "site-packages" in relative:
        continue
    sz = file.stat().st_size
    extracted_inventory.append({"path": relative, "size": sz})
    # Avoid scanning bundled third-party libraries beyond the named native code and *.pyc.
    if sz > 80_000_000:
        continue
    data = file.read_bytes()
    seen, matched = set(), []
    samples = [m.group().decode("ascii", "ignore") for m in ASCII_RX.finditer(data)]
    # Also collect literal wide strings (Windows-native binaries).
    for x in re.findall(rb"(?:[\x20-\x7e]\x00){8,}", data)[:10000]:
        samples.append(x.replace(b"\x00", b"").decode("ascii", "ignore"))
    for s in samples:
        for m in URL_RX.finditer(s):
            endpoint = m.group(0).rstrip(".,;:)]}")
            urls.setdefault(endpoint, set()).add(relative)
        if NEEDLE_RX.search(s):
            # Do not print arbitrary secrets, credential values, or long binary lines.
            line = s[:180]
            if re.search(r"(?i)password\s*=|secret\s*=|token\s*=|authorization\s*:", line):
                continue
            if line not in seen and len(matched) < 90:
                seen.add(line)
                matched.append(line)
    if matched:
        results.append({"path": relative, "bytes": sz, "matched_strings": matched})
    if relative == "BMW.exe":
        binary_flags = {
            "MZ_header": data[:2] == b"MZ",
            "pyinstaller_MEI_cookie_found": b"MEI\x0c\x0b\x0a\x0b\x0e" in data[-1048576:],
            "pyarmor_string_found": b"pyarmor" in data.lower(),
        }
        (OUT / "EXECUTABLE_FLAGS.json").write_text(json.dumps(binary_flags, indent=2))
    del data

(OUT / "REPOSITORY_BINARY_SCAN.json").write_text(
    json.dumps({"scanned_files": len(files_to_scan), "findings": results}, indent=2, ensure_ascii=False))
(OUT / "ENDPOINT_CANDIDATES.json").write_text(
    json.dumps([{"url": u, "files": sorted(v)} for u, v in sorted(urls.items())], indent=2))
(OUT / "EXTRACTED_FILE_INVENTORY.json").write_text(json.dumps(extracted_inventory, indent=2))

disassembled = 0
for file in EXTRACTED.rglob("*.pyc") if EXTRACTED.exists() else []:
    if disassembled >= 35 or file.stat().st_size > 2_000_000:
        continue
    try:
        data = file.read_bytes()
        if data[:4] != importlib.util.MAGIC_NUMBER:
            continue
        obj = marshal.loads(data[16:])
        if not isinstance(obj, type((lambda: 0).__code__)):
            continue
        stream = io.StringIO()
        stream.write("Python 3.11 static disassembly: " + str(file.relative_to(ROOT)) + "\n")
        dis.dis(obj, file=stream, depth=2)
        target = OUT / "disassembly" / (str(file.relative_to(EXTRACTED)).replace("/", "__") + ".txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(stream.getvalue()[:400_000], encoding="utf-8")
        disassembled += 1
    except (ValueError, TypeError, EOFError, OSError):
        continue

readme = f"""# BMW read-only static recovery checkpoint

Source: {ROOT.name}/BMW.exe (original file never executed or modified)

## Contents
- EXTRACTED_FILE_INVENTORY.json: paths and sizes of PyInstaller extracted material
- EXECUTABLE_FLAGS.json: PE / PyInstaller archive fingerprint
- ENDPOINT_CANDIDATES.json: URL-like ASCII / UTF16LE strings; candidates ONLY
- REPOSITORY_BINARY_SCAN.json: limited plain-text keyword matches, not full control-flow
- disassembly/: Python 3.11 bytecode from successfully extracted .pyc modules, if any
- BMW.exe_extracted/: extracted payload (archived separately by workflow)

## Interpretation
This is *unpacking*, not guaranteed recovery of the original .py source.
PyArmor runtime and any native .pyd modules can prevent restoration of original Python code.
A URL appearing in string data is not proof that it is a license endpoint.
Nothing here proves the request method, JSON body, or expected server response.
No executable was launched; no license was bypassed; no server was contacted.
Unknowns must be resolved by authorized source review and/or a controlled runtime capture.

Number of candidate scanned files: {len(files_to_scan)}
Number of disassembled pyc modules: {disassembled}
"""
(OUT / "README_RECOVERY.md").write_text(readme)
print("Static scan complete.")
print("Collected", len(urls), "URL candidates; disassembled", disassembled, ".pyc files")

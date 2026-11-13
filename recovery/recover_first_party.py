#!/usr/bin/env python3
"""Read-only Python 3.11 source recovery, without executing extracted modules."""
from __future__ import annotations
import ast, hashlib, importlib.util, json, marshal, os
from pathlib import Path
import subprocess, types

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"BMW.exe_extracted"
PYZ=BASE/"PYZ.pyz_extracted"
OUT=ROOT/"recovery-output"/"first_party_source"
VALID=OUT/"syntax_valid"
RAW=OUT/"unverified"
VALID.mkdir(parents=True,exist_ok=True)
RAW.mkdir(parents=True,exist_ok=True)
NAMES={"bmw_gui","runtime_bmw_paths","license_client","license_dialog",
       "device_id","bmw","bmw_config","settings_bmw","browser_bmw",
       "proxy_bmw","irctc_bmw"}
pathmap={}
for folder in (BASE,PYZ):
    for p in folder.glob("*.pyc"):
        if p.stem in NAMES:pathmap[p.stem]=p
top_names=sorted(p.stem for p in PYZ.glob("*.pyc"))
(OUT/"top_level_module_names.json").write_text(json.dumps(top_names,indent=2))
items=[]
for name,file in sorted(pathmap.items()):
    binary=file.read_bytes()
    row={"module":name,"pyc_path":str(file.relative_to(ROOT)),
         "pyc_bytes":len(binary),"sha256":hashlib.sha256(binary).hexdigest()}
    try:
        if binary[:4]!=importlib.util.MAGIC_NUMBER:
            raise ValueError("Python version bytecode mismatch")
        co=marshal.loads(binary[16:])
        row["top_level_code_length"]=len(co.co_code)
        row["nested_count"]=sum(isinstance(x,types.CodeType) for x in co.co_consts)
        row["is_protected_main"]=name=="bmw_gui" or ("pyarmor" in " ".join(co.co_names).lower())
        if row["is_protected_main"]:
            (RAW/(name+".NOTICE.txt")).write_text(
                "PyArmor protected stub. The original BMW app code is NOT recovered."
                " Original .pyc is in the unpacked archive. No bypass performed.\n")
            row["status"]="PROTECTED_MAIN_UNRECOVERED"
        else:
            run=subprocess.run([os.getenv("PYCDC_BIN","pycdc"),str(file)],
                text=True,encoding="utf-8",errors="replace",capture_output=True,timeout=50)
            recovered=run.stdout
            row["tool_exit_code"]=run.returncode
            row["tool_stderr"]=run.stderr[:1500]
            row["source_characters"]=len(recovered)
            if recovered.strip():
                (RAW/(name+".py.txt")).write_text(recovered,encoding="utf-8")
                try:
                    ast.parse(recovered)
                    if "unable to decompile" in recovered.lower():
                        row["status"]="HAS_DECOMPILER_PLACEHOLDER"
                    else:
                        (VALID/(name+".py")).write_text(recovered,encoding="utf-8")
                        row["status"]="SYNTAX_VALID_BEHAVIOR_UNVERIFIED"
                except SyntaxError as e:
                    row["status"]="INVALID_SYNTAX"
                    row["syntax_error"]=str(e)
            else:
                row["status"]="NO_SOURCE"
    except Exception as exc:
        row["status"]="ERROR"
        row["error"]=type(exc).__name__+": "+str(exc)[:180]
    items.append(row)
(OUT/"SOURCE_RECOVERY_REPORT.json").write_text(json.dumps(
    {"notice":"AST-valid output is not proof of original functionality. "
     "PyArmor-protected main remains unrecovered.","modules":items},indent=2))
for r in items:
    print(r["module"],r["status"],r["pyc_bytes"])
print("Top-level modules:",",".join(top_names[:140]))

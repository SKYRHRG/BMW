#!/usr/bin/env python3
"""BMW read-only main-module/license scan. Does not execute recovered code."""
from pathlib import Path
import importlib.util, marshal, types, json, re, hashlib
ROOT=Path(__file__).resolve().parents[1]
EXT=ROOT/"BMW.exe_extracted"
OUT=ROOT/"recovery-output"
OUT.mkdir(exist_ok=True)
pattern=re.compile(r"(?i)(license|licence|licen|activat|validat|expiry|expire|endpoint|server|verify|auth|subscription|fingerprint)")
urlrx=re.compile(r"(?i)(https?|wss?)://([A-Za-z0-9.-]+)(?::\d{2,5})?(/[A-Za-z0-9/_~.%+@=-]{0,120})?")
def scan_obj(obj,label,depth=0):
    if depth>4:return []
    names=sorted(set(str(n) for n in obj.co_names))
    snippets=[x for x in names if pattern.search(x)][:100]
    out=[{"code_object":label,"name":obj.co_name,"bytecode_length":len(obj.co_code),"names_matching_license":snippets,"all_names_preview":names[:100],"nested_objects":sum(isinstance(x,types.CodeType) for x in obj.co_consts),"string_constants":sum(isinstance(x,str) for x in obj.co_consts)}]
    for c in obj.co_consts:
        if isinstance(c,types.CodeType):out.extend(scan_obj(c,label+"/"+c.co_name,depth+1))
    return out
targets=["bmw_gui.pyc","runtime_bmw_paths.pyc"]
report={"source":"static marshal inspection only","targets":{},"module_filename_hits":[]}
for target in targets:
    f=EXT/target
    if f.exists():
        try:
            data=f.read_bytes()
            if data[:4]!=importlib.util.MAGIC_NUMBER:raise ValueError("Python bytecode header differs from this runner")
            obj=marshal.loads(data[16:])
            report["targets"][target]={"file_size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"code":scan_obj(obj,target)}
        except Exception as e:
            report["targets"][target]={"error":type(e).__name__+": "+str(e)[:120]}
for f in EXT.rglob("*.pyc"):
    if pattern.search(str(f.relative_to(EXT))):
        report["module_filename_hits"].append(str(f.relative_to(EXT)))
(OUT/"MAIN_MODULE_CODE_STRUCTURE.json").write_text(json.dumps(report,indent=2))
print("=== Target code structure (limited to names and counts) ===")
for target,d in report["targets"].items():
    print(target, "size:",d.get("file_size"),"error:",d.get("error"))
    for c in d.get("code",[])[:8]:
        print("object",c["code_object"],"code_bytes",c["bytecode_length"],"nested",c["nested_objects"],"names_matching",c["names_matching_license"])
print("license-related module filenames",report["module_filename_hits"][:25])

#!/usr/bin/env python3
"""BMW targeted license config inspection. Reads .pyc statically only."""
import dis
import importlib.util
import marshal
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "BMW.exe_extracted"
dialog = EX / "PYZ.pyz_extracted" / "license_dialog.pyc"
client = EX / "PYZ.pyz_extracted" / "license_client.pyc"
main = EX / "bmw_gui.pyc"
def load(path):
    data=path.read_bytes()
    assert data[:4]==importlib.util.MAGIC_NUMBER
    return marshal.loads(data[16:])
def out(title, value):
    print(f"{title}: {value}")
for label,path in [("dialog",dialog),("client",client),("main_protected",main)]:
    if not path.exists():
        out(label, "MISSING");continue
    co=load(path)
    out(label+" bytecode_length", len(co.co_code))
    out(label+" top_name_contains_LICENSE_API_URL", "LICENSE_API_URL" in co.co_names)
    out(label+" top_const_contains_LICENSE_API_URL", "LICENSE_API_URL" in co.co_consts)
    out(label+" contains_os_environ", "environ" in co.co_names)
    out(label+" contains_get", "get" in co.co_names)
    out(label+" has_pyarmor_main", "__pyarmor__" in co.co_names)
    if label=="dialog":
        instructions=list(dis.get_instructions(co))
        print("### TOP-LEVEL MODULE INSTRUCTIONS (last 110) ###")
        for ins in instructions[-110:]:
            print(f"{ins.offset:4} {ins.opname:27} {str(ins.argrepr)[:85]}")
        print("### DIALOG CLASS CONSTRUCTOR SIGNATURE ###")
        for c in co.co_consts:
            if isinstance(c,types.CodeType) and c.co_name=="LicenseDialog":
                for inner in c.co_consts:
                    if isinstance(inner,types.CodeType) and inner.co_name=="__init__":
                        print("args",inner.co_varnames[:inner.co_argcount],"kwonly",inner.co_kwonlyargcount)
                        print("constructor names",inner.co_names)
                        print("constructor literal url?",[x for x in inner.co_consts if isinstance(x,str) and "http" in x])
print("### STATIC ONLY. THIS DOES NOT CONFIRM ORIGINAL EXE HONORS ENV OVERRIDE ###")

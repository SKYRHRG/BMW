#!/usr/bin/env python3
"""Extract *read-only* License API bytecode instruction trace, never executing app."""
from pathlib import Path
import importlib.util,marshal,types,dis,io
root=Path(__file__).resolve().parents[1]
base=root/"BMW.exe_extracted"/"PYZ.pyz_extracted"
out=root/"recovery-output";out.mkdir(exist_ok=True)
def crawl(x):
    yield x
    for v in x.co_consts:
        if isinstance(v,types.CodeType):yield from crawl(v)
def load(f):
    b=f.read_bytes()
    if b[:4]!=importlib.util.MAGIC_NUMBER:raise RuntimeError("Wrong bytecode version")
    return marshal.loads(b[16:])
for target,which in [("license_client.pyc",{"check_license","_pick_msg"}),("license_dialog.pyc",{"_persist_fauth_result","_on_finish","<module>"})]:
    f=base/target
    obj=load(f)
    lines=[]
    for c in crawl(obj):
        if c.co_name not in which:continue
        lines.append(f"\n######## {target} / {c.co_name} starts at line {c.co_firstlineno} ########")
        for ins in dis.get_instructions(c,show_caches=False):
            val = str(ins.argrepr)
            if len(val)>160:val=val[:160]+"... <truncated>"
            # Unicode output could include credentials in constants; do not print long constants
            lines.append(f"{ins.offset:5d} {ins.opname:<29} {val}")
    report="\n".join(lines)
    (out/(target+".disassembly.txt")).write_text(report)
    print("DISASSEMBLY FOR",target,"total",len(lines),"instructions, files written")
    if target=="license_client.pyc":
        print("\n".join(lines[:460]))

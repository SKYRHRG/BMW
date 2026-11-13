#!/usr/bin/env python3
"""Read-only metadata + selected bytecode excerpts for Step 2; never imports extracted modules."""
import dis, importlib.util, marshal, json, types
from pathlib import Path
base=Path("BMW.exe_extracted/PYZ.pyz_extracted")
files={"client":base/"license_client.pyc","dialog":base/"license_dialog.pyc","device":base/"device_id.pyc"}
for label,path in files.items():
    print("### FILE",label,path.name,"present",path.exists())
    if not path.exists():continue
    raw=path.read_bytes()
    if raw[:4]!=importlib.util.MAGIC_NUMBER:
        print("Unexpected bytecode magic");continue
    co=marshal.loads(raw[16:])
    objects=[]
    def walk(obj):
        objects.append(obj)
        for c in obj.co_consts:
            if isinstance(c,types.CodeType):walk(c)
    walk(co)
    print("OBJECTS",len(objects))
    for ob in objects[:30]:
        names=[x for x in ob.co_names if any(k in x.lower() for k in ["licens","key","url","device","machine","set","jwt","sig","uuid","sha"])]
        print("META",ob.co_name,"args",ob.co_argcount, "kwonly",ob.co_kwonlyargcount, "varnames",repr(ob.co_varnames[:15]),"firstlineno",ob.co_firstlineno,"codelen",len(ob.co_code),"names",names[:30])
    if label=="client":
        obj=next((x for x in objects if x.co_name=="<module>"),None)
        if obj:
            for instr in dis.get_instructions(obj):
                if instr.opname=="LOAD_CONST" and isinstance(instr.argval,str):
                    if len(instr.argval)<160:print("MODULE_CONST",repr(instr.argval))
        fn=next((x for x in objects if x.co_name=="check_license"),None)
        if fn:
            print("CHECK_LICENSE_RETURN_BRANCH_TAIL_BEGIN")
            for instr in dis.get_instructions(fn):
                if instr.offset>=1650:
                    val=str(instr.argrepr)
                    if len(val)>140:val=val[:140]+"..."
                    print(instr.offset,instr.opname,val)
            print("CHECK_LICENSE_RETURN_BRANCH_TAIL_END")
    if label=="dialog":
        for n in ["_persist_fauth_result","_on_finish"]:
            ob=next((x for x in objects if x.co_name==n),None)
            if not ob:continue
            print("DIALOG_VALUES",n)
            print("STR_CONSTANTS",repr([x for x in ob.co_consts if isinstance(x,str) and len(x)<150][:90]))

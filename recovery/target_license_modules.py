#!/usr/bin/env python3
"""Read-only license-client .pyc inspection. NO code execution."""
from pathlib import Path
import importlib.util,marshal,types,re,json,hashlib
root=Path(__file__).resolve().parents[1]
base=root/"BMW.exe_extracted"/"PYZ.pyz_extracted"
out=root/"recovery-output"
out.mkdir(exist_ok=True)
keywords=re.compile(r"(?i)licen[cs]|activat|validat|expire|expiry|server|endpoint|api|verify|device|fingerprint|auth|http|https|request|post|get|json|status|success|fail|key|url|machine|subscription|nonce")
urlrx=re.compile(r"(?i)(https?|wss?)://[a-z0-9._:-]+(?:/[a-z0-9/_~.%+=@-]{0,160})?")
def walk(co,where,depth=0):
    if depth>6:return []
    consts=[x for x in co.co_consts if isinstance(x,str)]
    # Avoid exposing embedded license credentials, authorization and tokens
    samples=[]
    for s in consts:
        if len(s)>300: continue
        if keywords.search(s):
            if re.search(r"(?i)(bearer\s+\S+|api[_-]?key\s*[:=]|password\s*[:=]|private[_-]?key)",s):
                continue
            samples.append(s[:180])
    names=list(dict.fromkeys(str(x) for x in co.co_names))
    children=[x for x in co.co_consts if isinstance(x,types.CodeType)]
    result=[{"path":where,"function":co.co_name,"line":co.co_firstlineno,"bytecode_bytes":len(co.co_code),
             "names":names[:150],"matching_strings":samples[:90],"nested_count":len(children),
             "pyarmor_import":any("pyarmor" in s.lower() for s in names)}]
    for c in children:result+=walk(c,where+"/"+c.co_name,depth+1)
    return result
report={}
for name in ["license_client.pyc","license_dialog.pyc","bmw_gui.pyc"]:
    path=(base/name) if (base/name).exists() else (root/"BMW.exe_extracted"/name)
    if not path.exists():report[name]={"error":"missing"};continue
    try:
        d=path.read_bytes()
        if d[:4]!=importlib.util.MAGIC_NUMBER:raise ValueError("wrong magic")
        obj=marshal.loads(d[16:])
        report[name]={"size":len(d),"sha256":hashlib.sha256(d).hexdigest(),"code":walk(obj,name)}
    except Exception as e:report[name]={"error":type(e).__name__+": "+str(e)[:150]}
(out/"LICENSE_MODULE_STRUCTURE.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
for name,data in report.items():
    print("TARGET",name,"size",data.get("size"),"error",data.get("error"))
    for obj in data.get("code",[])[:22]:
        print("OBJECT",obj["path"],"line",obj["line"],"bytecode",obj["bytecode_bytes"],"nested",obj["nested_count"])
        print("NAMES",json.dumps(obj["names"][:65]))
        print("SELECTED CONSTANTS",json.dumps(obj["matching_strings"][:35]))

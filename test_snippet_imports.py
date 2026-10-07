"""Golden expectations and failure cases. Inputs are fictional, never executed."""
import contextlib
import io
import json
import time
import tracemalloc
import tempfile
from pathlib import Path
from snippet_imports import pick_imports, ReviewRequired, main

cases=[
 ('select only required imports','import json\nimport time\ndef f(s):\n    return json.loads(s)\n',3,4,['import json']),
 ('alias','import json as j\ndef f(s):\n    return j.loads(s)\n',2,3,['import json as j']),
 ('partial multi import','import json, os\nx = json.dumps({})\n',2,2,['import json']),
 ('from multi import','from statistics import mean, median\nx = mean([1,2])\n',2,2,['from statistics import mean']),
 ('multiline alias','from statistics import (\n    mean as avg,\n    median,\n)\nx = avg([1,2])\n',5,5,['from statistics import mean as avg']),
 ('parameter shadow','import json\ndef f(json):\n    return json\n',2,3,[]),
 ('local assignment shadow','import json\ndef f():\n    json = 3\n    return json\n',2,4,[]),
 ('nested global','import json\ndef f():\n    def g(s):\n        return json.loads(s)\n    return g\n',2,5,['import json']),
 ('nested closure','import json\ndef f(json):\n    def g():\n        return json\n    return g\n',2,5,[]),
 ('comprehension shadow','import json\nx = [json for json in [1,2]]\n',2,2,[]),
 ('decorator','from functools import lru_cache\n@lru_cache()\ndef f():\n    return 1\n',2,4,['from functools import lru_cache']),
 ('static annotation','from pathlib import Path\ndef f(p: Path):\n    return p\n',2,3,['from pathlib import Path']),
 ('future static annotation','from __future__ import annotations\nfrom pathlib import Path\ndef f(p: Path) -> Path:\n    return p\n',3,4,['from __future__ import annotations','from pathlib import Path']),
 ('dotted import','import xml.etree.ElementTree\nx = xml.etree.ElementTree.Element("x")\n',2,2,['import xml.etree.ElementTree']),
 ('relative import','from .thing import Thing\nx = Thing()\n',2,2,['from .thing import Thing']),
 ('string and comment not name','import json\nx = "json"  # json.loads\n',2,2,[]),
 ('preserve selected import','import json\nx = json.loads("[]")\n',1,2,[]),
 ('input never executed','import os\nraise RuntimeError("do not execute")\ndef f():\n    return os.name\n',3,4,['import os']),
 ('unicode function','import json\ndef výsledek(s):\n    return json.loads(s)\n',2,3,['import json']),
]
failures=[
 ('incomplete function','import json\ndef f():\n    return json.dumps({})\n',3,3),
 ('missing decorator','from functools import lru_cache\n@lru_cache()\ndef f():\n    return 1\n',3,4),
 ('wildcard','from math import *\nx = sqrt(3)\n',2,2),
 ('module rebinding','import json\njson = fake\ndef f(s):\n    return json.loads(s)\n',3,4),
 ('selected module rebinding','import json\nx=json.dumps({})\njson=3\n',2,3),
 ('function global rebinding','import json\ndef f():\n    global json\n    json=3\n    return json\n',2,5),
 ('unsupported class scope','import json\nclass C:\n    json=3\n    x:json\n',2,4),
 ('duplicate binding','import json\nimport other as json\nx=json.dumps({})\n',3,3),
 ('conditional import','if True:\n    import json\nx=json.dumps({})\n',3,3),
 ('dynamic lookup','import json\nx=globals()["json"].dumps({})\n',2,2),
 ('string annotation','from pathlib import Path\ndef f(p: "Path"):\n    return p\n',2,3),
 ('syntax error','import json\nx = (\n',2,2),
 ('range error','x=1\n',0,1),
 ('oversize','x=1\n' * 26000,1,1),
]
out=[]
for name,source,start,end,expected in cases:
 r=pick_imports(source,start,end)
 assert r['imports']==expected,(name,r['imports'],expected)
 assert r['code'].endswith(''.join(source.splitlines(keepends=True)[start-1:end])),name
 assert r==pick_imports(source,start,end),name+' nondeterministic duplicate'
 out.append(dict(name=name,passed=True,kind='fictional supported golden'))
for name,source,start,end in failures:
 try:pick_imports(source,start,end)
 except ReviewRequired:out.append(dict(name=name,passed=True,kind='fictional manual review expected'))
 else:raise AssertionError('silently accepted unsupported case '+name)
r=pick_imports('def f():\n    return missing(2)\n',1,2)
assert r['unresolved_names']==['missing']
out.append(dict(name='unresolved context surfaced',passed=True))
r=pick_imports('len=custom_length\ndef f(x):\n    return len(x)\n',2,3)
assert r['unresolved_names']==['len']
out.append(dict(name='shadowed builtin context surfaced',passed=True))
with tempfile.TemporaryDirectory(prefix='snippet-imports-test-') as folder:
 p=Path(folder)/'fictional.py';p.write_text('import json\nx=json.dumps({})\n');old=p.read_bytes()
 stop=Path(folder)/'STOP'
 def invoke(path):
  stdout=io.StringIO();stderr=io.StringIO()
  with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
   rc=main([str(path),'--lines','2:2','--stop-file',str(stop)])
  return rc,stdout.getvalue(),stderr.getvalue()
 a=invoke(p);b=invoke(p);assert a==b and a[0]==0 and p.read_bytes()==old
 out.append(dict(name='CLI duplicates read only',passed=True))
 stop.touch();a=invoke(p);assert a[0]==2 and not a[1]
 stop.unlink();a=invoke(p);assert a[0]==0 and p.read_bytes()==old
 out.append(dict(name='CLI stop and recovery',passed=True))
 a=invoke(Path(folder)/'absent.py');assert a[0]==2 and not a[1] and folder not in a[2]
 out.append(dict(name='CLI missing input no partial output',passed=True))
large='import json\n'+''.join(f'def f{i}(s):\n    return json.loads(s)\n' for i in range(1000))
tracemalloc.start();started=time.perf_counter();r=pick_imports(large,2000,2001);elapsed=time.perf_counter()-started
_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
assert r['imports']==['import json'] and elapsed<1 and peak<32*1024*1024
print(json.dumps(dict(status='pass',fictional_tests=out,count=len(out),performance=dict(source_bytes=len(large.encode()),seconds=elapsed,parser_peak_bytes=peak),source_executed=False,network_calls=0,api_cash_eur=0,human_intervention_not_measured=True),indent=2))

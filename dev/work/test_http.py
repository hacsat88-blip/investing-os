import json
import urllib.request
import urllib.error
import csv
import io

base='http://127.0.0.1:8765'
state=json.load(urllib.request.urlopen(base+'/api/state'))
headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':state['token']}
def post(path,body,custom=None):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers=custom if custom is not None else headers)
    try:
        with urllib.request.urlopen(req) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,{'error':'rejected'}
assert post('/api/preview',state)[0]==200
stale={**state,'version':'0'*32}
assert post('/api/preview',stale)[0]==409
assert post('/api/preview',state,{**headers,'Origin':'https://untrusted.example'})[0]==403
assert post('/api/preview',state,{**headers,'Host':'untrusted.example'})[0]==403
assert post('/api/preview',state,{'Content-Type':'application/json','Origin':base})[0]==403
for table in state['tables']:
    text=urllib.request.urlopen(base+'/api/csv?table='+table).read().decode('utf-8-sig')
    assert list(csv.DictReader(io.StringIO(text)))==state['tables'][table]
    code,data=post('/api/import-csv',{'table':table,'csv':text})
    assert code==200 and data['rows']==state['tables'][table]
assert post('/api/backup',{})[0]==200
print('HTTP preview / stale version / origin / host / CSRF / six CSV roundtrips / backup: PASS')

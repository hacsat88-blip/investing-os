import argparse
import csv
import io
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from store import Store, SCHEMAS, validate, summary
from insights import research_queue, risks, simulate, compare, health

STORE=Store()
TOKEN=secrets.token_urlsafe(32)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def send(self,code,data,kind='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)):
            data=json.dumps(data,ensure_ascii=False).encode()
        if isinstance(data,str):
            data=data.encode()
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)

    def do_GET(self):
        if not self.host_ok():
            return self.send(403,{'error':'Invalid host'})
        path=urlparse(self.path).path
        try:
            if path in ('/','/app.js','/insights.js','/style.css'):
                name={'/':'index.html','/app.js':'app.js','/insights.js':'insights.js','/style.css':'style.css'}[path]
                kind={'/':'text/html; charset=utf-8','/app.js':'application/javascript','/insights.js':'application/javascript','/style.css':'text/css'}[path]
                return self.send(200,(Path(__file__).parent/name).read_bytes(),kind)
            if path=='/api/state':
                state=STORE.read()
                state.update({'token':TOKEN,'schemas':SCHEMAS,'history':STORE.history(),'backupPath':str(STORE.root/'backups')})
                state['insights']={'queue':research_queue(state['tables']),'risk':risks(state['tables']),'comparison':compare(state['tables']),'health':health(STORE,state)}
                return self.send(200,state)
            if path=='/api/export':
                return self.send(200,STORE.read())
            if path=='/api/csv':
                table=parse_qs(urlparse(self.path).query).get('table',[''])[0]
                if table not in SCHEMAS:
                    raise ValueError('不明な台帳')
                state=STORE.read()
                return self.send(200,(STORE.data/'revisions'/state['version']/(table+'.csv')).read_bytes(),'text/csv; charset=utf-8')
            self.send(404,{'error':'Not found'})
        except Exception as e:
            self.send(400,{'error':str(e)})

    def do_POST(self):
        origin='http://127.0.0.1:'+str(self.server.server_port)
        if not self.host_ok() or self.headers.get('Origin')!=origin or self.headers.get('X-CSRF-Token')!=TOKEN:
            return self.send(403,{'error':'編集元を確認できません'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=5_000_000:
                raise ValueError('入力サイズが不正です')
            body=json.loads(self.rfile.read(length))
            path=urlparse(self.path).path
            if path=='/api/simulate':
                state=STORE.read()
                if body['version']!=state['version']:raise ValueError('CONFLICT: 最新版を再読してください')
                return self.send(200,simulate(state['tables'],body['pricePct'],body['fxPct']))
            if path=='/api/preview':
                state=STORE.read()
                if body['version']!=state['version']:
                    raise ValueError('CONFLICT: 最新版を再読してから統合してください')
                validate(body['tables'])
                return self.send(200,{'changes':STORE.diff(state['tables'],body['tables']),'summary':summary(body['tables'])})
            if path=='/api/commit':
                return self.send(200,STORE.commit(body['tables'],body['version'],body.get('actor','USER'),body['reason']))
            if path=='/api/restore-preview':
                return self.send(200,{'tables':STORE.restore_tables(body['target'])})
            if path=='/api/import-csv':
                table=body['table']
                if table not in SCHEMAS:
                    raise ValueError('不明な台帳')
                reader=csv.DictReader(io.StringIO(body['csv'].lstrip('\ufeff')))
                if reader.fieldnames!=SCHEMAS[table]:
                    raise ValueError('CSVの列順が違います。アプリから出力したCSVを使用してください')
                rows=list(reader)
                tables=STORE.read()['tables']
                tables[table]=rows
                validate(tables)
                return self.send(200,{'rows':rows})
            if path=='/api/backup':
                return self.send(200,{'path':STORE.backup_revision(STORE.read()['version'])})
            self.send(404,{'error':'Not found'})
        except Exception as e:
            self.send(409 if 'CONFLICT' in str(e) else 400,{'error':str(e)})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    STORE.read()
    STORE.backup_revision(STORE.read()['version'])
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url='http://127.0.0.1:'+str(server.server_port)
    print('investingOS: '+url,flush=True)
    print('保存のたびにMacへバックアップします。終了は Control+C。',flush=True)
    if args.open:
        threading.Timer(0.4,lambda:webbrowser.open(url)).start()
    server.serve_forever()

if __name__=='__main__':
    main()

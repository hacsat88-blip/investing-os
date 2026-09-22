"""CSV-first portfolio store. Standard-library only; local use, no brokerage API."""
import argparse
import copy
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from insights import EXTRA_SCHEMAS, validate_extra

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    'holdings': 'id scope bucket code name account currency quantity avgCost costBasisJpy price fx priceAsOf marketValueJpy pnlJpy tags quality sourceId note'.split(),
    'targets': 'id code name role weight status sourceId note'.split(),
    'analyses': 'id code title asOf conclusion rationale counterCase falsifier nextReview status sourceId note'.split(),
    'sources': 'id kind title uri publishedAt retrievedAt dataAsOf confidence note'.split(),
    'news': 'id code title publishedAt retrievedAt priceAsOf price pts ptsAsOf ptsVolume close closeAsOf stars direction confidence sourceId summary reviewAction'.split(),
    'decisions': 'id code asOf status proposal approvalEvidence executionEvidence sourceId note'.split(),
}
SCHEMAS.update(EXTRA_SCHEMAS)
NUMBERS = {'quantity','avgCost','costBasisJpy','price','fx','marketValueJpy','pnlJpy','weight','pts','ptsVolume','close','stars','impact','uncertainty','urgency','effort','additionalCashJpy','feesJpy','taxJpy','targetValueJpy','value'}
SIGNED = {'pnlJpy'}
# 撤回条件欄だけは反証エンジンの記法で始められる（27-falsification.md）。他の列・他の先頭文字は従来どおり拒否する。
FALSIFY_PREFIX = ('@falsify ', '@stale ')

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def number(value):
    if value == '' or value is None:
        return None
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('数値として読めません: ' + str(value))
    if not n.is_finite():
        raise ValueError('NaN・無限大は保存できません')
    return n

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')

def csv_bytes(table, rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=SCHEMAS[table], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return ('\ufeff' + out.getvalue()).encode('utf-8')

def validate(tables):
    if set(tables) != set(SCHEMAS):
        raise ValueError('最新版の全台帳が必要です。ChatGPT用データを再出力してください')
    for table, rows in tables.items():
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError('行数が不正です')
        ids = set()
        for row in rows:
            if set(row) != set(SCHEMAS[table]) or any(not isinstance(v,str) for v in row.values()):
                raise ValueError(table + ': 列または値の型が不正です')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', row['id']) or row['id'] in ids:
                raise ValueError(table + ': IDが空・重複・不正です')
            ids.add(row['id'])
            for key, value in row.items():
                if len(value) > 30000:
                    raise ValueError('セルが長すぎます')
                if key in NUMBERS:
                    n = number(value)
                    if n is not None and key not in SIGNED and n < 0:
                        raise ValueError(key + ': 負の値は保存できません')
                    if n is not None and key == 'fx' and n <= 0:
                        raise ValueError('FXは正の数が必要です')
                elif key == 'falsifier' and value.lstrip().startswith(FALSIFY_PREFIX):
                    pass  # 反証エンジンの記法（knowledge/27-falsification.md）。@は表計算の式にならないため撤回条件欄のみ許可。
                elif value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                    raise ValueError(key + ': 表計算ソフトの式として解釈される先頭文字は使えません')
            if table == 'holdings':
                if row['scope'] not in ('taxable','ideco') or row['quality'] not in ('FACT','EST','UNKNOWN'):
                    raise ValueError('scope または quality が不正です')
                if not row['name'] or row['currency'] not in ('JPY','USD'):
                    raise ValueError('名称と対応通貨 JPY / USD が必要です')
                if row['bucket'] not in ('目標構成','保留枠','守備枠','年金コア'):
                    raise ValueError('枠が不正です')
                if (row['scope'] == 'ideco') != (row['bucket'] == '年金コア'):
                    raise ValueError('iDeCoと年金コアの範囲が一致しません')
            if table in ('analyses','decisions'):
                if row['status'] not in ('PROPOSED','APPROVED','EXECUTED'):
                    raise ValueError('判断状態が不正です')
                if table == 'analyses' and row['status'] == 'EXECUTED':
                    raise ValueError('分析自体は売買の実行記録ではありません')
                if table == 'decisions':
                    if row['status'] in ('APPROVED','EXECUTED') and not row['approvalEvidence']:
                        raise ValueError('承認根拠が必要です')
                    if row['status'] == 'EXECUTED' and not row['executionEvidence']:
                        raise ValueError('約定の実行根拠が必要です')
            if table == 'targets' and row['status'] not in ('PROPOSED','ACTIVE','INACTIVE'):
                raise ValueError('目標の状態が不正です')
            if table == 'news':
                stars = number(row['stars'])
                if stars is not None and (stars != int(stars) or not 1 <= stars <= 5):
                    raise ValueError('星は1〜5、取得不能は空欄にしてください')
                if row['direction'] not in ('POSITIVE','NEGATIVE','MIXED','NEUTRAL','UNKNOWN'):
                    raise ValueError('ニュースの方向が不正です')
    source_ids = {r['id'] for r in tables['sources']}
    for table, rows in tables.items():
        if table != 'sources':
            for r in rows:
                if not r['sourceId'] or any(s not in source_ids for s in r['sourceId'].split(';')):
                    raise ValueError(table + ': sourceIdはSourcesのIDを指定してください（複数は;区切り）')
    active = [r for r in tables['targets'] if r['status'] == 'ACTIVE']
    if active and (any(number(r['weight']) is None for r in active) or abs(sum(number(r['weight']) for r in active)-1) > Decimal('0.000001')):
        raise ValueError('有効な目標配分は合計1.0にしてください。欠損を自動調整しません')
    validate_extra(tables)

def summary(tables):
    values, issues = [], []
    for r in tables['holdings']:
        reported = number(r['marketValueJpy'])
        q, p, fx = (number(r[k]) for k in ('quantity','price','fx'))
        calculated = q*p*fx if all(v is not None for v in (q,p,fx)) else None
        if r['scope'] == 'ideco':
            value = reported
        else:
            value = calculated
            if calculated is None:
                issues.append(r['name'] + ': 数量・価格・FX不足。評価額は未算定')
            elif reported is not None and abs(reported-calculated) > 1:
                issues.append(r['name'] + ': 報告評価額と再計算が不一致')
                value = None
        cost = number(r['costBasisJpy'])
        pnl = value-cost if value is not None and cost is not None else None
        if r['scope'] == 'ideco':
            pnl = number(r['pnlJpy'])
        if pnl is None:
            issues.append(r['name'] + ': 円建て損益は未確定')
        if not r['priceAsOf']:
            issues.append(r['name'] + ': 評価基準日なし')
        values.append({'id':r['id'],'name':r['name'],'scope':r['scope'],'bucket':r['bucket'], 'value':float(value) if value is not None else None,'pnl':float(pnl) if pnl is not None else None,'tags':r['tags'], 'asOf':r['priceAsOf']})
    dates = sorted(set(r['priceAsOf'] for r in tables['holdings']))
    if len(dates)>1:
        issues.append('評価基準日が混在しています。同時点の資産総額ではありません')
    issues.append('現金・未収配当・他口座の網羅性は未確認。表示は登録資産の参考値です')
    missing = sum(r['value'] is None for r in values)
    subtotal = sum(r['value'] for r in values if r['value'] is not None)
    return {'rows':values,'subtotal':subtotal,'missing':missing,'dates':dates,'issues':issues,
            'taxable':sum(r['value'] for r in values if r['scope']=='taxable' and r['value'] is not None),
            'ideco':sum(r['value'] for r in values if r['scope']=='ideco' and r['value'] is not None),
            'pnlSubtotal':sum(r['pnl'] for r in values if r['pnl'] is not None), 'pnlMissing':sum(r['pnl'] is None for r in values)}

class Store:
    def __init__(self, root=ROOT):
        self.root=Path(root)
        self.data=self.root/'data'
        self.data.mkdir(parents=True,exist_ok=True)

    @contextmanager
    def lock(self):
        with (self.data/'.lock').open('a') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def read(self):
        pointer=json.loads((self.data/'current.json').read_text())
        return self.read_revision(pointer['version'])

    def read_revision(self, version):
        if not re.fullmatch(r'[a-f0-9]{32}',version):
            raise ValueError('版IDが不正です')
        folder=self.data/'revisions'/version
        meta=json.loads((folder/'manifest.json').read_text())
        tables={}
        for table in SCHEMAS:
            if table in EXTRA_SCHEMAS and table not in meta['hashes'] and meta.get('schemaVersion') in ('4.2','4.3'):
                tables[table]=[]
                continue
            raw=(folder/(table+'.csv')).read_bytes()
            if digest(raw)!=meta['hashes'][table]:
                raise ValueError('CSVの整合性エラー。直接編集せず復元または再取込みしてください')
            tables[table]=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        validate(tables)
        return {'version':version,'meta':meta,'tables':tables,'summary':summary(tables)}

    def diff(self, old, new):
        changes=[]
        for table in SCHEMAS:
            a={r['id']:r for r in old.get(table,[])}
            b={r['id']:r for r in new[table]}
            for rid in sorted(a.keys()|b.keys()):
                if a.get(rid)!=b.get(rid):
                    changes.append({'table':table,'id':rid,'before':a.get(rid),'after':b.get(rid)})
        return changes

    def commit(self, tables, version, actor, reason):
        validate(tables)
        if not reason.strip() or actor not in ('USER','AI','MIGRATION','RESTORE'):
            raise ValueError('変更理由と編集者が必要です')
        with self.lock():
            old=self.read() if (self.data/'current.json').exists() else None
            if (old['version'] if old else None) != version:
                raise ValueError('CONFLICT: 他の編集を検出。再読して差分を統合してください')
            changes=self.diff(old['tables'] if old else {},tables)
            if old and not changes:
                return old
            # Audit and decisions are never silently removed or rewritten.
            if old:
                current_decisions={r['id']:r for r in tables['decisions']}
                for row in old['tables']['decisions']:
                    if current_decisions.get(row['id'])!=row:
                        raise ValueError('判断履歴は追記のみです。訂正行を追加してください')
            vid=uuid.uuid4().hex
            folder=self.data/'revisions'/vid
            folder.mkdir(parents=True)
            hashes={}
            for table in SCHEMAS:
                raw=csv_bytes(table,tables[table])
                hashes[table]=digest(raw)
                atomic(folder/(table+'.csv'),raw)
            meta={'version':vid,'parent':version,'savedAt':now(),'actor':actor,'reason':reason,'hashes':hashes,'changes':changes,'schemaVersion':'4.4'}
            atomic(folder/'manifest.json',json_bytes(meta))
            check=self.read_revision(vid)
            self.backup_revision(vid)
            atomic(self.data/'current.json',json_bytes({'version':vid}))
            return check

    def backup_revision(self, version):
        self.read_revision(version)
        folder=self.data/'revisions'/version
        target=self.root/'backups'/(version+'.zip')
        target.parent.mkdir(exist_ok=True)
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.iterdir()):
                z.write(path,path.name)
        raw=out.getvalue()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if z.testzip() is not None:
                raise ValueError('バックアップ検証失敗')
            manifest=json.loads(z.read('manifest.json'))
            for table in manifest['hashes']:
                if digest(z.read(table+'.csv')) != manifest['hashes'][table]:
                    raise ValueError('バックアップのハッシュ不一致')
        atomic(target,raw)
        return str(target)

    def history(self):
        current=self.read()['version']
        results=[]
        # Only reachable committed revisions; abandoned writes never appear as history.
        while current:
            meta=json.loads((self.data/'revisions'/current/'manifest.json').read_text())
            results.append({k:meta[k] for k in ('version','parent','savedAt','actor','reason')})
            current=meta['parent']
        return results

    def restore_tables(self, version):
        tables=self.read_revision(version)['tables']
        # Restoration rolls holdings/research back, while preserving the append-only ledger.
        tables['decisions']=self.read()['tables']['decisions']
        existing={r['id'] for r in tables['sources']}
        for row in self.read()['tables']['sources']:
            if row['id'] not in existing:
                tables['sources'].append(row)
        return tables

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['read','backup','proposal'])
    parser.add_argument('--input')
    parser.add_argument('--output')
    args=parser.parse_args()
    store=Store()
    state=store.read()
    if args.command=='read':
        print(json.dumps(state,ensure_ascii=False,indent=2))
    elif args.command=='backup':
        print(store.backup_revision(state['version']))
    else:
        candidate=json.loads(Path(args.input).read_text())
        if candidate['version']!=state['version']:
            raise ValueError('CONFLICT: 提案の元データが古くなっています')
        validate(candidate['tables'])
        candidate['changes']=store.diff(state['tables'],candidate['tables'])
        atomic(Path(args.output),json_bytes(candidate))
        print('提案を保存しました。アプリで読み込み、差分を確認してください')

if __name__=='__main__':
    main()

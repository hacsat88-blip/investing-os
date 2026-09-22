"""Decision-support calculations; assumptions never mutate actual positions."""
import json
import zipfile
from datetime import datetime, timezone, timedelta

EXTRA_SCHEMAS = {
 'theses':'id holdingId reason expectation metric baseline latest threshold change counterCase falsifier reviewOn reviewedAt thesisStatus sourceId note'.split(),
 'research':'id holdingId question decisionLink impact uncertainty urgency effort dueOn researchStatus nextAction result sourceId note'.split(),
 'exposures':'id holdingId dimension component weight asOf quality sourceId note'.split(),
 'plans':'id title mode baselineHash additionalCashJpy feesJpy taxJpy benefit risk assumptions invalidation status sourceId note'.split(),
 'plan_items':'id planId holdingId code name bucket targetValueJpy sourceId note'.split(),
 'checks':'id subject checkedAt checkStatus detail sourceId note'.split(),
 'quotes':'id holdingId code kind value currency asOf retrievedAt quality sourceId note'.split(),
}

def validate_extra(tables):
    from store import number
    holdings={r['id'] for r in tables['holdings']}
    plans={r['id'] for r in tables['plans']}
    for name in ('theses','research','exposures'):
        for row in tables[name]:
            if row['holdingId'] and row['holdingId'] not in holdings:
                raise ValueError(name+': 保有IDが見つかりません')
            if name in ('theses','exposures') and not row['holdingId']:
                raise ValueError(name+': 保有IDが必要です')
    seen=set()
    for r in tables['theses']:
        if r['holdingId'] in seen: raise ValueError('銘柄カードは保有IDごとに1件です')
        seen.add(r['holdingId'])
        if r['thesisStatus'] not in ('UNREVIEWED','SUPPORTED','WATCH','CHALLENGED'):
            raise ValueError('投資仮説の状態が不正です')
    for r in tables['research']:
        if r['researchStatus'] not in ('OPEN','IN_PROGRESS','DONE','BLOCKED'): raise ValueError('調査状態が不正です')
        for field in ('impact','uncertainty','urgency','effort'):
            v=number(r[field])
            if v is not None and (v!=int(v) or not 1<=v<=5): raise ValueError(field+': 1〜5で入力してください')
    totals={};seen=set()
    for r in tables['exposures']:
        if r['dimension'] not in ('ISSUER','SECTOR','CURRENCY'): raise ValueError('内訳分類が不正です')
        if not r['component']: raise ValueError('内訳項目が必要です')
        key=(r['holdingId'],r['dimension'],r['component'])
        if key in seen: raise ValueError('同じ保有・分類・内訳が重複しています')
        seen.add(key)
        if r['quality'] not in ('FACT','EST','UNKNOWN'): raise ValueError('内訳の品質が不正です')
        weight=number(r['weight'])
        if weight is not None:
            if not 0<=weight<=1: raise ValueError('内訳比率は0〜1です')
            if not r['asOf']: raise ValueError('内訳比率には基準日が必要です')
            k=key[:2];totals[k]=totals.get(k,0)+weight
    if any(v>1 for v in totals.values()): raise ValueError('同一保有の同一分類の比率合計が1を超えています')
    for r in tables['plans']:
        if r['mode'] not in ('HOLD','ADD','REBALANCE') or r['status'] not in ('PROPOSED','APPROVED'):
            raise ValueError('比較案の種別・状態が不正です')
    seen=set()
    for r in tables['plan_items']:
        if r['planId'] not in plans: raise ValueError('比較案IDが見つかりません')
        if r['holdingId']:
            if r['holdingId'] not in holdings: raise ValueError('比較明細の保有IDが見つかりません')
            key=(r['planId'],r['holdingId'])
        else:
            if not r['code'] or not r['name']: raise ValueError('未保有候補はコードと名称が必要です')
            key=(r['planId'],'NEW:'+r['code'])
        if key in seen: raise ValueError('比較明細が重複しています')
        seen.add(key)
    for r in tables['checks']:
        if r['subject'] not in ('HOLDINGS','NOTIFICATION','EXTERNAL_BACKUP'): raise ValueError('点検対象が不正です')
        if r['checkStatus'] not in ('UNKNOWN','CONFIRMED','FAILED'): raise ValueError('点検状態が不正です')
        if r['checkStatus']=='CONFIRMED' and (not r['checkedAt'] or not r['detail']): raise ValueError('確認済みには日時と確認内容が必要です')
    seen=set()
    for r in tables['quotes']:
        if r['kind'] not in ('PRICE','NAV','FX'):
            raise ValueError('相場の種別はPRICE / NAV / FXです')
        if r['quality'] not in ('FACT','EST','UNKNOWN'):
            raise ValueError('相場の品質が不正です')
        if r['kind']=='FX':
            if r['holdingId']:
                raise ValueError('FXは保有IDを空欄にし、codeへ通貨ペアを入れてください')
            if not r['code']:
                raise ValueError('FXにはcode（例 USDJPY）が必要です')
        else:
            if r['holdingId'] not in holdings:
                raise ValueError('quotes: 保有IDが見つかりません')
        value=number(r['value'])
        if value is None or value<=0:
            raise ValueError('相場の値は正の数が必要です')
        if r['currency'] not in ('JPY','USD'):
            raise ValueError('相場の通貨はJPY / USDです')
        if not r['asOf']:
            raise ValueError('相場には基準日時が必要です')
        if not r['sourceId']:
            raise ValueError('相場には出典IDが必要です')
        key=(r['holdingId'] or r['code'],r['kind'],r['asOf'])
        if key in seen:
            raise ValueError('同じ対象・種別・基準日時の相場が重複しています')
        seen.add(key)
    for name,fields in {'theses':['reviewOn','reviewedAt'],'research':['dueOn'],'exposures':['asOf'],'checks':['checkedAt'],'quotes':['asOf','retrievedAt']}.items():
        for r in tables[name]:
            for field in fields:
                if r[field]: parse_date(r[field],strict=True)

def parse_date(value, strict=False):
    try:
        # Legacy values may carry a human-readable session suffix.
        text=value.replace('Z','+00:00')
        if strict:
            dt=datetime.fromisoformat(text)
        else:
            dt=datetime.fromisoformat(text[:10])
        return dt.replace(tzinfo=timezone(timedelta(hours=9))) if dt.tzinfo is None else dt
    except (ValueError,TypeError):
        if strict: raise ValueError('日時はISO形式（例 2026-09-13 または 2026-09-13T12:00:00+09:00）で入力してください')
        return None

def research_queue(tables, at=None):
    from store import number
    today=(at or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=9))).date()
    rows=[]
    for r in tables['research']:
        if r['researchStatus']=='DONE':continue
        scores=[number(r[k]) for k in ('impact','uncertainty','urgency')]
        score=int(scores[0]*scores[1]+2*scores[2]) if all(x is not None for x in scores) else None
        due=parse_date(r['dueOn'])
        rows.append({**r,'score':score,'overdue':bool(due and due.date()<today)})
    return sorted(rows,key=lambda r:(not r['overdue'],r['score'] is None,-(r['score'] or 0),int(r['effort'] or 5),r['id']))

def risks(tables):
    from store import summary, number
    s=summary(tables);values={r['id']:r['value'] for r in s['rows']}
    denominator=s['subtotal'] if not s['missing'] and s['subtotal']>0 else None
    tags={}
    for r in s['rows']:
        if r['value'] is None:continue
        for tag in set(x.strip() for x in r['tags'].split(',') if x.strip()):
            tags[tag]=tags.get(tag,0)+r['value']
    dimensions={}
    for dimension in ('ISSUER','SECTOR','CURRENCY'):
        components={};covered=0;dated=set();est=False
        for r in tables['exposures']:
            if r['dimension']!=dimension or r['quality']=='UNKNOWN':continue
            value=values[r['holdingId']];weight=number(r['weight'])
            if value is None or weight is None:continue
            amount=value*float(weight);covered+=amount
            components[r['component']]=components.get(r['component'],0)+amount
            dated.add(r['asOf']);est=est or r['quality']=='EST'
        dimensions[dimension]={'components':sorted(components.items(),key=lambda kv:-kv[1]),'covered':covered,'unmappedKnown':max(0,s['subtotal']-covered),'coverage':covered/denominator if denominator else None,'dates':sorted(dated),'hasEstimates':est}
    return {'tags':sorted(tags.items(),key=lambda kv:-kv[1]),'dimensions':dimensions,'denominator':denominator,'missing':s['missing']}

def simulate(tables, price_pct, fx_pct):
    from store import summary, number
    p=number(str(price_pct));f=number(str(fx_pct))
    if p is None or f is None or not -100<=p<=500 or not -100<=f<=500:
        raise ValueError('変化率は-100〜500%の範囲で入力してください')
    s=summary(tables);currencies={r['id']:r['currency'] for r in tables['holdings']};rows=[]
    for r in s['rows']:
        v=r['value'];after=None if v is None else v*(1+float(p)/100)*(1+float(f)/100 if currencies[r['id']]=='USD' else 1)
        rows.append({'name':r['name'],'before':v,'after':after,'change':None if after is None else after-v})
    return {'rows':rows,'before':s['subtotal'],'after':sum(r['after'] for r in rows if r['after'] is not None),'missing':s['missing'],'pricePct':float(p),'fxPct':float(f)}

def compare(tables):
    from store import summary, number, digest, csv_bytes
    s=summary(tables);holdings={r['id']:r for r in tables['holdings']}
    baseline={r['id']:r for r in s['rows']};baseline_hash=digest(csv_bytes('holdings',tables['holdings']))
    results=[]
    for p in tables['plans']:
        problems=[];warnings=[]
        if p['baselineHash']!=baseline_hash:problems.append('比較元の保有データが異なります。再読して比較案を見直してください')
        if s['missing']:problems.append('元の評価額に未算定があります')
        inputs=[number(p[k]) for k in ('additionalCashJpy','feesJpy','taxJpy')]
        if any(v is None for v in inputs):problems.append('追加資金・費用・税の入力が不足（0円も明示入力）')
        positions={rid:r['value'] for rid,r in baseline.items()}
        buckets={rid:holdings[rid]['bucket'] for rid in positions}
        names={rid:holdings[rid]['name'] for rid in positions}
        items=[r for r in tables['plan_items'] if r['planId']==p['id']]
        if p['mode']=='HOLD' and items:problems.append('現状維持案には変更明細を追加できません')
        for item in items:
            rid=item['holdingId'] or 'NEW:'+item['code'];value=number(item['targetValueJpy'])
            if value is None:problems.append(item['name']+': 提案評価額が未入力')
            v=float(value) if value is not None else None
            if item['holdingId']:
                old=baseline[rid]['value']
                if p['mode']=='ADD' and old is not None and v is not None and v<old:problems.append('追加資金案に既存保有の縮小が含まれています')
                if v!=old and holdings[rid]['bucket'] in ('保留枠','守備枠','年金コア'):warnings.append(names[rid]+': 保護対象の枠を変更する提案です。方針変更の明示承認が別途必要')
            else:names[rid]=item['name'];buckets[rid]=item['bucket'] or '未指定'
            positions[rid]=v
        if p['mode']=='HOLD' and inputs[0] is not None and inputs[0]!=0:problems.append('現状維持案の追加資金は0円にしてください')
        if problems:
            results.append({**p,'problems':problems,'ready':False});continue
        added,fees,tax=map(float,inputs)
        total=s['subtotal']+added-fees-tax
        invested=sum(positions.values());cash=total-invested
        if cash < -0.01:problems.append('必要資金が予算を超えています')
        allocations=[{'name':names[rid],'value':v,'weight':v/total if total>0 else None,'change':v-(baseline[rid]['value'] if rid in baseline else 0),'bucket':buckets[rid]} for rid,v in positions.items()]
        allocations.sort(key=lambda r:-r['value'])
        results.append({**p,'ready':not problems,'problems':problems,'warnings':warnings,'netAssets':total,'cash':cash,'positions':allocations,'maxWeight':max((r['weight'] for r in allocations if r['weight'] is not None),default=None),'top3Weight':sum(r['value'] for r in allocations[:3])/total if total>0 else None})
    return {'baselineHash':baseline_hash,'results':results,'scope':'登録資産＋追加資金。未収録の既存現金は含みません。金額配分の比較であり約定可能株数・売買推奨ではありません。'}

def health(store, state, at=None):
    from store import digest
    at=at or datetime.now(timezone.utc)
    rows=[]
    for r in state['tables']['holdings']:
        dt=parse_date(r['priceAsOf']);days=max(0,(at-dt).days) if dt else None
        rows.append({'name':r['name'],'asOf':r['priceAsOf'],'ageDays':days,'status':'UNKNOWN' if dt is None else 'REVIEW' if days>7 else 'RECORDED'})
    backup=store.root/'backups'/(state['version']+'.zip');backup_status='MISSING'
    if backup.exists():
        try:
            with zipfile.ZipFile(backup) as z:
                meta=json.loads(z.read('manifest.json'))
                ok=meta['version']==state['version'] and all(digest(z.read(k+'.csv'))==v for k,v in state['meta']['hashes'].items())
                backup_status='VERIFIED' if ok and z.testzip() is None else 'FAILED'
        except Exception:backup_status='FAILED'
    monitoring={'status':'UNVERIFIED','lastAttemptAt':None,'lastSuccessAt':None,'detail':'実行証拠がありません'}
    path=store.root/'monitoring/state.json'
    if path.exists():
        try:
            raw=json.loads(path.read_text())
            valid=raw.get('lastStatus') in ('SUCCESS','PARTIAL','FAILED','SKIPPED') and parse_date(raw.get('lastAttemptAt','')) is not None
            report=raw.get('reportPath','');resolved=(store.root/'monitoring'/report).resolve()
            valid=valid and bool(report) and (store.root/'monitoring').resolve() in resolved.parents and resolved.is_file()
            if valid:monitoring={'status':raw['lastStatus'],'lastAttemptAt':raw.get('lastAttemptAt'),'lastSuccessAt':raw.get('lastSuccessAt'),'detail':raw.get('detail',''),'reportPath':report}
        except Exception:monitoring['detail']='監視状態ファイルを検証できません'
    confirmations={}
    for subject in ('HOLDINGS','NOTIFICATION','EXTERNAL_BACKUP'):
        found=[r for r in state['tables']['checks'] if r['subject']==subject]
        confirmations[subject]=max(found,key=lambda r:r['checkedAt'],default=None)
    return {'prices':rows,'backup':backup_status,'backupVersion':state['version'],'monitoring':monitoring,'confirmations':confirmations,'evaluatedAt':at.isoformat(),'staleThresholdDays':7}


# --- v4.4: 相場台帳（quotes.csv）の鮮度・整合チェック ------------------------
# 価格は保有台帳（数量・取得原価）とは更新頻度が違うため、出典付きの相場行として
# 別に記録する。ここでは判定のみを行い、保有台帳は書き換えない。

FRESH_DAYS = 3
STALE_DAYS = 7
MISMATCH_PCT = 0.5


def _latest(rows, key):
    best = {}
    for r in rows:
        dt = parse_date(r['asOf'])
        if dt is None:
            continue
        k = key(r)
        if k not in best or dt > best[k][0]:
            best[k] = (dt, r)
    return {k: v[1] for k, v in best.items()}


def quote_status(tables, at=None):
    from store import number
    at = at or datetime.now(timezone.utc)
    quotes = tables.get('quotes', [])
    prices = _latest([r for r in quotes if r['kind'] in ('PRICE', 'NAV')], lambda r: r['holdingId'])
    fx = _latest([r for r in quotes if r['kind'] == 'FX'], lambda r: r['code'].upper())
    rows = []
    for h in tables['holdings']:
        book = number(h['price'])
        q = prices.get(h['id'])
        entry = {
            'holdingId': h['id'], 'name': h['name'], 'currency': h['currency'],
            'bookPrice': float(book) if book is not None else None, 'bookAsOf': h['priceAsOf'],
            'quotePrice': None, 'quoteAsOf': None, 'quoteKind': None, 'quality': None,
            'sourceId': None, 'ageDays': None, 'deltaPct': None, 'status': 'NO_QUOTE',
            'detail': '出典付きの相場行がありません',
        }
        if q is not None:
            value = number(q['value'])
            dt = parse_date(q['asOf'])
            age = max(0, (at - dt).days) if dt else None
            entry.update({
                'quotePrice': float(value), 'quoteAsOf': q['asOf'], 'quoteKind': q['kind'],
                'quality': q['quality'], 'sourceId': q['sourceId'], 'ageDays': age,
            })
            if book is not None and book > 0:
                entry['deltaPct'] = round(float((value - book) / book * 100), 4)
            if age is None:
                entry.update(status='UNKNOWN', detail='相場の基準日時を解釈できません')
            elif age > STALE_DAYS:
                entry.update(status='STALE', detail='相場が%d日前です。再取得してください' % age)
            elif entry['deltaPct'] is not None and abs(entry['deltaPct']) >= MISMATCH_PCT:
                entry.update(status='MISMATCH', detail='保有台帳の価格と%.2f%%ずれています' % entry['deltaPct'])
            elif age > FRESH_DAYS:
                entry.update(status='AGING', detail='相場が%d日前です' % age)
            else:
                entry.update(status='FRESH', detail='%d日前の出典付き相場です' % age)
        rows.append(entry)
    fx_rows = []
    for code, r in sorted(fx.items()):
        dt = parse_date(r['asOf'])
        fx_rows.append({'code': code, 'value': float(number(r['value'])), 'asOf': r['asOf'],
                        'quality': r['quality'], 'sourceId': r['sourceId'],
                        'ageDays': max(0, (at - dt).days) if dt else None})
    counts = {}
    for r in rows:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    return {'evaluatedAt': at.isoformat(), 'freshDays': FRESH_DAYS, 'staleDays': STALE_DAYS,
            'mismatchPct': MISMATCH_PCT, 'holdings': rows, 'fx': fx_rows, 'counts': counts,
            'note': '判定のみ。保有台帳の価格はユーザーが差分を承認するまで変更しない。'}

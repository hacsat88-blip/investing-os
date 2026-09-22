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
    for name,fields in {'theses':['reviewOn','reviewedAt'],'research':['dueOn'],'exposures':['asOf'],'checks':['checkedAt']}.items():
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

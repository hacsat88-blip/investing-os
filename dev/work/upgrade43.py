# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'outputs/investingOS-v4.2'
p=ROOT/'app/app.js';t=p.read_text()
t=t.replace("const names={holdings:","const names={theses:'投資仮説',research:'調査課題',exposures:'構成内訳',plans:'比較案',plan_items:'比較明細',checks:'点検記録',holdings:")
t=t.replace("const labels={id:","const labels={holdingId:'保有ID',reason:'保有理由',expectation:'期待する変化',metric:'確認指標',baseline:'前回値・時点',latest:'最新値・時点',threshold:'判定基準',change:'前回からの変化',reviewOn:'次回確認日',reviewedAt:'確認日時',thesisStatus:'仮説状態',question:'調査課題',decisionLink:'判断への関係',impact:'判断影響1〜5',uncertainty:'不確実性1〜5',urgency:'緊急度1〜5',effort:'負担1〜5',dueOn:'調査期限',researchStatus:'調査状態',nextAction:'次の調査',result:'判明したこと',dimension:'内訳分類',component:'構成項目',mode:'案の種別',baselineHash:'比較元ハッシュ',additionalCashJpy:'追加資金・円',feesJpy:'費用仮定・円',taxJpy:'税仮定・円',benefit:'期待効果',risk:'リスク',assumptions:'前提',invalidation:'見直す条件',planId:'比較案ID',targetValueJpy:'提案評価額・円',subject:'点検対象',checkedAt:'確認日時',checkStatus:'点検状態',detail:'確認内容',id:")
t=t.replace("const hints={holdings:","const hints={theses:'保有理由・確認指標・撤回条件を固定IDで追跡します。',research:'保存すると優先順位を再計算します。各点数は1〜5、未採点は空欄。',exposures:'比率は小数（20%は0.2）。未取得部分を100%へ補正しません。',plans:'現状維持・追加資金・組替えを金額で比較。0円も明示入力。保存で再計算。',plan_items:'保有IDを指定して提案評価額を入力。未記載の保有は維持。新候補は保有IDを空欄にしてコード・名前・枠を入力。',checks:'実際に確認した日時と内容を記録します。設定済みと動作確認済みは別です。',holdings:")
t=t.replace("const long=new Set([", "const long=new Set(['reason','expectation','change','question','decisionLink','nextAction','result','benefit','risk','assumptions','invalidation','detail',")
t=t.replace("const enums={scope:","const enums={thesisStatus:['UNREVIEWED','SUPPORTED','WATCH','CHALLENGED'],researchStatus:['OPEN','IN_PROGRESS','DONE','BLOCKED'],dimension:['ISSUER','SECTOR','CURRENCY'],mode:['HOLD','ADD','REBALANCE'],subject:['HOLDINGS','NOTIFICATION','EXTERNAL_BACKUP'],checkStatus:['UNKNOWN','CONFIRMED','FAILED'],scope:")
t=t.replace("function render(){dashboard();", "function render(){dashboard();renderInsights();")
t=t.replace("current==='analyses'?['PROPOSED','APPROVED']", "['analyses','plans'].includes(current)?['PROPOSED','APPROVED']")
t=t.replace("'保存ごとにCSV全6種と変更履歴をZIP保存。保存先：'", "'保存ごとに全CSVと変更履歴をZIP保存。保存先：'")
t=t.replace("if('status'in row)row.status='PROPOSED';", "if(current==='theses')row.thesisStatus='UNREVIEWED';if(current==='research')row.researchStatus='OPEN';if(current==='exposures')Object.assign(row,{dimension:'ISSUER',quality:'UNKNOWN'});if(current==='checks')Object.assign(row,{subject:'HOLDINGS',checkStatus:'UNKNOWN'});if(current==='plans')Object.assign(row,{mode:'HOLD',baselineHash:state.insights.comparison.baselineHash});if('status'in row)row.status='PROPOSED';")
t=t.replace("else await load();}}catch(e)", "else await load();}else if(insightTab==='health'){state.insights.health=remote.insights.health;renderInsights();}}catch(e)")
p.write_text(t)
css=ROOT/'app/style.css'
css.write_text(css.read_text()+'''\n.insight-panel{margin-bottom:22px}.insight-panel nav{margin-bottom:22px;flex-wrap:wrap}.thesis-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px;margin:18px 0}.thesis-card,.subpanel{border:1px solid #e0e7dc;border-radius:9px;padding:17px;background:#fbfcf9}.thesis-card{margin:0}.thesis-card summary{font-size:13px;font-weight:600;line-height:1.8}.thesis-card[open]{grid-column:1/-1}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}.insight-field{display:flex;flex-direction:column;gap:7px;font-size:12px}.insight-field textarea{min-height:75px;width:100%;resize:vertical}.insight-field input{width:100%}.mini-grid{overflow:auto;max-height:460px;margin:14px 0}.mini-grid th{position:sticky;top:0}.mini-grid td{padding:11px;min-width:90px;max-width:350px;white-space:normal;line-height:1.7}.subpanel h3{font-size:15px}.subpanel p{font-size:12px;overflow-wrap:anywhere}.attention{color:#976123}.subpanel .actions label{font-size:12px;display:flex;flex-direction:column;gap:5px}.insight-panel>.muted{margin-top:22px}@media(max-width:650px){.form-grid{grid-template-columns:1fr}.thesis-grid{grid-template-columns:1fr}}\n''')
sys.path.insert(0,str(ROOT/'app'))
from store import Store, SCHEMAS, csv_bytes, digest
store=Store(ROOT);state=store.read();tables=state['tables']
(ROOT/'audit/before-v4.3.json').write_text(json.dumps({'version':state['version'],'hashes':state['meta']['hashes']},indent=2))
def row(table,**values):
    r={k:'' for k in SCHEMAS[table]};r.update(values);return r
sid='SRC43_REQUEST'
tables['sources'].append(row('sources',id=sid,kind='USER_PRIMARY',title='2026-09-13 機能①②③④⑥の追加とChatGPT原則運用の依頼',uri='この会話のユーザー指示',retrievedAt='2026-09-13',dataAsOf='2026-09-13',confidence='SINGLE_SOURCE',note='機能追加の根拠。投資仮説、構成比、最新価格、保有確認の根拠ではない。'))
for holding in tables['holdings']:
    tables['theses'].append(row('theses',id='TH_'+holding['id'],holdingId=holding['id'],thesisStatus='UNREVIEWED',sourceId=sid,note='入力用カード。保有理由・指標・撤回条件はユーザーとの確認待ち。'))
for i,(question,link,action) in enumerate([
 ('最新保有と現金・他口座の範囲を確認','比較案の母集団を確定する','最新の保有テキストまたは画面を照合'),
 ('ETF・投信の構成銘柄と構成日を確認','個別株・年金コアとの重複を検証する','運用会社の最新月報・構成資料を取得'),
 ('MUUの円建て取得原価を確認','円建て損益の未確定を解消する','取得時の明細を確認。現在FXで逆算しない'),
 ('各銘柄の保有理由と撤回条件を確認','ニュースが投資仮説に与える影響を追えるようにする','ユーザーの保有理由を確認し一次開示と照合')],1):
    tables['research'].append(row('research',id=f'RQ{i:03}',question=question,decisionLink=link,researchStatus='OPEN',nextAction=action,sourceId=sid,note='機能導入時の調査候補。点数は未採点。'))
baseline=digest(csv_bytes('holdings',tables['holdings']))
tables['plans'].append(row('plans',id='PLAN_HOLD',title='現状維持（比較の基準）',mode='HOLD',baselineHash=baseline,additionalCashJpy='0',feesJpy='0',taxJpy='0',benefit='取引をしない場合の比較基準',risk='現在の登録資産の集中・価格変動をそのまま維持',assumptions='追加資金・売買費用・売買税は0円と仮定。未収録現金は含めない。',invalidation='保有データ更新時は基準を再確認',status='PROPOSED',sourceId=sid))
for pid,title,mode in [('PLAN_ADD','追加資金で調整（入力待ち）','ADD'),('PLAN_REBALANCE','一部組替え（入力待ち）','REBALANCE')]:
    tables['plans'].append(row('plans',id=pid,title=title,mode=mode,baselineHash=baseline,status='PROPOSED',sourceId=sid,note='追加資金・費用・税・明細を入力するまで試算未完了。承認済み方針ではない。'))
saved=store.commit(tables,state['version'],'MIGRATION','ユーザー承認の①②③④⑥を追加。保有・目標・判断履歴は変更なし')
for name in ('holdings','targets','decisions'):
    assert csv_bytes(name,saved['tables'][name])==csv_bytes(name,state['tables'][name])
print('Upgraded',saved['version'])

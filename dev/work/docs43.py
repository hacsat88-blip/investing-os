# -*- coding: utf-8 -*-
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'outputs/investingOS-v4.2'
STAGE=ROOT.parent/'investingOS_ChatGPT-update'
STAGE.mkdir(exist_ok=True)
def write(name,text):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n')
old=ROOT/'PROJECT-INSTRUCTIONS-v4.2.md'
text=old.read_text().replace('v4.2','v4.3').replace('内の6つのCSV','内の全CSV（12種）')
text=text.replace('## 正本と接続','''## 原則運用と正本
ChatGPTでの運用を原則とする。調査、分析、提案、助言、ユーザーとの確認はChatGPTを主な窓口とする。Claude Artifactの「投資判断台帳」は運用上の正本として使用しない。Claude固有のread_db/write_db、Chrome拡張、Project配置済み等を前提にしない。
「主なAI運用先」と「保存データの正本」を区別する。ChatGPTの会話や添付コピーを独立した正本にせず、下記のCSV台帳へ承認済み差分を反映して初めて同期済みとする。ChatGPTからMacへ直接アクセスできない環境では、データ出力→ChatGPTで分析・提案→更新案取込→ユーザー確認保存で運用する。

## データ保存と接続''')
text=text.replace('## 必須境界','''## 追加された分析・管理機能
① 投資仮説：theses.csv。保有IDごとに保有理由、期待する変化、確認指標、前回値・最新値、基準、前回からの変化、反対仮説、撤回条件、次回確認、出典を記録。未確認の保有理由を創作しない。
② 調査優先順位：research.csv。判断に影響する未確認事項を列挙し、影響・不確実性・緊急度・負担（各1〜5）、期限、次の調査を記録。期限超過を先に、影響×不確実性＋緊急度×2の降順、同点は負担昇順。未採点は不明のまま。点数は利益確率や銘柄推奨点ではない。
③ 重複・ストレス：exposures.csvで構成銘柄・業種・通貨の内訳を基準日と出典付き記録。タグ重複と構成比の集計を区別。未取得分を再正規化しない。ストレスは商品価格変化率とUSD建て行のFX変化率の仮定計算であり予測ではない。
④ 提案比較：plans.csvとplan_items.csv。現状維持・追加資金・組替えを同じ保存済み保有に対し比較。追加資金・費用・税の欠損、基準の陳腐化、予算不足を表示。提案はPROPOSED。金額配分の比較であり発注株数を生成しない。保護枠の変更案には別の方針変更承認が必要。
⑥ 健康状態：checks.csv、監視の実行記録、バックアップ検査を使用。保有確認、価格日付と経過日数、監視の最終試行・最終成功、通知到達、Macの現在版ZIP、別媒体バックアップを別表示。未確認を確認済みとしない。
詳しい手順はknowledge/60-decision-workbench.mdと70-health-and-chatgpt.mdを参照。⑤の判断成績の自動振り返りは今回の追加対象外。

## 必須境界''')
text=text.replace('Google/Claude Project配置','ChatGPT Project配置')
write('PROJECT-INSTRUCTIONS.md',text)
write('PROJECT-INSTRUCTIONS-v4.2.md','''# 旧ファイル名の案内
現行指示は PROJECT-INSTRUCTIONS.md（v4.3）です。この案内をProject指示欄に貼らず、現行ファイルの全文を使用してください。
ChatGPT原則運用、正本データはCSV。旧Claude Artifactを正本として使用しません。
''')
for p in (ROOT/'knowledge').glob('*.md'):
 t=p.read_text().replace('v4.2','v4.3').replace('全6CSV','全12CSV').replace('CSV全6種','CSV全12種').replace('CSV全6種','CSV全12種').replace('同版のCSV全6種','同版のCSV全12種')
 t=t.replace('Claudeの金融スキルはClaude環境で実在・利用可能な場合に使用する。Codexでは利用可能な金融スキルを用い、別サービスの能力が移植済みと仮定しない。','ChatGPTで利用可能な金融スキル・接続ツールを必要に応じて用いる。Claude固有スキルの利用を必須条件にしない。ツールがない場合は一次資料のWeb確認または提供資料で代替し、不足を明示する。')
 p.write_text(t)
write('knowledge/60-decision-workbench.md','''
# 60 投資仮説・調査課題・重複・提案比較 v4.3

## ① 投資仮説カード
保有IDごとに1枚。reason/expectation/metric/baseline/latest/threshold/change/counterCase/falsifier/reviewOn/reviewedAt/thesisStatus/sourceIdを保存する。
UNREVIEWED（未確認）/SUPPORTED（支持）/WATCH（注視）/CHALLENGED（反証材料）を使う。仮説状態と売買状態は別。未確認の指標や保有理由は空欄。コードだけでなく保有IDで口座の違いを保つ。
ニュース・決算を読んだら、どの仮説と指標に関係するかを示す。最新値と前回値の単位・期間を揃え、変化、理由、一次資料を記録する。材料だけで機械的に仮説を破壊済みとしない。

## ② 調査優先順位
question、decisionLink、impact、uncertainty、urgency、effort、dueOn、researchStatus、nextAction、result、sourceId。数値は各1〜5または空欄。
期限超過→影響×不確実性＋緊急度×2の降順→同点は負担の小さい順。完了は待ち行列から外す。未採点を0点とみなさず別表示。点数の理由はnoteへ記載し、精密な予測としない。
次の調査には「決算説明資料の利益率内訳を確認」のように対象と判定目的を書く。確認できたらresultと出典を残し、解決した課題だけDONEにする。

## ③ 重複とストレス
exposuresはholdingId、dimension（ISSUER/SECTOR/CURRENCY）、component、weight（0〜1の小数）、asOf、quality、sourceId。
同一保有・分類・構成要素は重複不可。同一保有・分類の合計は1以下。未知・未登録分は未割当として残す。集計は親商品の登録評価額×取得済み構成比。各分類内で集計し、銘柄・業種・通貨を互いに足さない。部分構成データを100%へ再正規化しない。
タグ集計はタグが付いた商品の評価額合計であり、ETFの組入比率・相関・実質デルタではない。確認済み構成情報のない商品を名称だけで自動分類しない。価格評価日と構成日が異なる場合は両方を示す。
ストレス式：評価額×(1＋商品価格変化率)×(1＋FX変化率)。FX項はUSD建て行のみ。率はパーセント入力。商品価格変化率は商品そのものへの仮定なので、レバレッジ倍率を再度掛けない。円建て海外投信の内包FX、相関変化、日次レバレッジの経路は未モデル化。予測・最大損失・推奨として出さない。欠損時は部分小計と未算定件数を表示。

## ④ 提案比較
plansにはtitle、mode（HOLD/ADD/REBALANCE）、baselineHash、additionalCashJpy、feesJpy、taxJpy、benefit、risk、assumptions、invalidation、status、sourceId。
plan_itemsにはplanId、holdingId（未保有候補は空欄）、code/name/bucket、targetValueJpy、sourceId。保有IDがあるとき銘柄・枠は保有台帳から取得。未記載の保有は現状維持。新候補はコード・名称を必要とするが、その同一性・商品性は別途確認する。
比較対象は登録資産＋追加資金。未収録の既存現金は含めない。調整後資産＝登録小計＋追加資金−費用−税。未配分資金＝調整後資産−提案評価額合計。マイナスなら資金不足。最大商品比率と上位3商品比率は未配分資金も含む分母で算定。
追加資金案は保有縮小を含めない。現状維持は追加資金0・変更明細なし。税と費用の空欄を0にしない。金額配分の試算であり、売買単位・実行可能株数や商品内の実質重複を完全に評価するものではない。
baselineHashは比較元holdings.csvのハッシュ。元データ変更後は案を再検討し、単にハッシュを書き換えて古い判断を新しく見せない。保護枠の変更を含む案は別の方針変更承認が必要。画面の保存・比較は保有やTargetを変更しない。
''')
write('knowledge/70-health-and-chatgpt.md','''
# 70 ChatGPT運用と健康状態 v4.3

主なAI運用先はChatGPT。正本は単一のCSV台帳。ChatGPTの会話は調査・提案・確認の窓口であり、旧Claude Artifact DBやGoogle Sheetsへの同期を要求しない。
クラウドのChatGPT Projectにファイルを置くだけではMac上のCSVへ直接アクセスできると仮定しない。アクセスできない環境では「AI用データ出力」→ChatGPTへ提示→version/tables/reasonを含む提案JSON→アプリ取込→差分承認保存を使う。ローカル接続が許可された環境のみapp/store.py read/proposalを利用する。サービスの内部DBや未提供ツールに依存しない。
根拠：OpenAI公式「プロジェクトとチャット」 https://learn.chatgpt.com/ja-JP/docs/projects （2026-09-13確認）。本指示を作成したことと、ChatGPT Projectへ登録したことは別。

## 健康状態の判断
checks.csvのsubjectはHOLDINGS/NOTIFICATION/EXTERNAL_BACKUP、checkStatusはUNKNOWN/CONFIRMED/FAILED。確認日時と根拠を記録。記入された確認済みは自己申告の記録であり、アプリが口座や通知先へ接続した証拠ではない。
価格・評価日付は行ごとに表示。7暦日超は要更新の目安（市場カレンダー未適用）。保存日時を価格基準日や保有確認日にすり替えない。
Macバックアップは現在版ZIPを開き、CSVのSHA-256を現在版と照合する。設定済みだけで検証済みにしない。別媒体バックアップは別の確認欄にする。

## 監視状態ファイル
monitoring/state.jsonは次の契約とする。lastAttemptAt、lastSuccessAtはタイムゾーン付きISO日時。lastStatusはSUCCESS/PARTIAL/FAILED/SKIPPED。reportPathはmonitoring/からの相対パスで、実在する当該回のレポートを指定。detailに取得範囲・欠測を短く記載。未実行ならファイルを成功状態で初期化しない。
lastAttemptAtは各回を記録。lastSuccessAtは必要範囲を確認できた回のみ更新し、PARTIAL/FAILEDで直近成功を上書きしない。銘柄別/経路別カーソルは別キーcursorsに保持し、取得失敗で進めない。
実行レポートがない状態や形式不正は未検証。定期登録済みと実行成功とスマホ到達は別。アプリを開いている間は健康表示を更新する。接続断時は読込エラーを表示し、古い表示を現在の成功結果としない。
自動監視の処理はChatGPT/Codex側の定期タスクに依存する。アプリ自体にはAIや市場データAPIを内蔵していない。
''')
readme='''# investingOS v4.3 — ChatGPT原則運用

ChatGPTを調査・分析・提案・助言の主な窓口とし、承認済みデータはCSV台帳へ保存します。Claude Artifactの「投資判断台帳」は運用上の正本として使用しません。Google Sheetsへの更新も行いません。

## 最初に使うもの
- AIの指示欄：PROJECT-INSTRUCTIONS.md の全文。
- Projectナレッジ：knowledge/の8文書。
- 相互編集アプリ：起動.command。http://127.0.0.1:8765 を開きます。
- 保有・分析の正本：アプリフォルダのdata/current.jsonが指すCSV全12種。

アプリの設置場所は既存の保存先と定期監視との互換性のため investingOS-v4.2 というフォルダ名を維持し、内容をv4.3へ更新しています。フォルダ名は正本の版番号ではありません。

## 追加した機能
① 銘柄ごとの投資仮説カード：保有理由、指標、変化、撤回条件を直接編集。
② 調査の優先順位：結論を左右する未確認事項を、期限・影響・不確実性・緊急度・負担で整理。
③ 重複・ストレス：タグの重複、取得済み構成情報の集計、価格・USD/JPY仮定の損失額表示。
④ 提案比較：現状維持・追加資金・一部組替えを同じ基準の金額配分で比較。現保有やTargetは自動更新しません。
⑥ 健康状態：保有確認、価格日付、監視の最終試行/成功、通知到達、現在版ZIPの検証、別媒体保存を区別。

## ChatGPTとの使い方
テキスト・スクショはChatGPTへ。「AI用データを出力」した最新版も渡し、分析や提案JSONを作成します。アプリで更新案を取り込み、あなたが修正し、差分を承認して保存します。会話だけで保存済み・売買実行済みにはなりません。ローカル接続がある場合だけ直接ファイルを読む経路を利用できます。
カードや表の編集は「変更理由」→「差分を確認して保存」。保存済みの値で優先順位・比較・集計を再計算します。ストレスは画面上の仮定計算です。

## 初期状態と留保
保有10件の数量・取得原価・目標配分・判断履歴は変更していません。仮説カードは未確認、構成情報は未登録、追加資金/組替え案は入力待ちです。初期の課税口座価格は9月11日、iDeCo評価は8月29日。最新保有・現金・他口座との照合が必要です。
バックアップは保存時・起動時にMac内へ自動保存。別媒体保存とMacログイン時の自動起動は未設定。監視設定は1日4回ですが、実際の成功・スマホ到達は別途確認します。
今回のローカルファイル更新と、ChatGPTのProjectへのアップロードは別です。旧資料の「Project配置済み」「Claude通知が稼働中」等は現在の事実として継承しません。旧通知の停止は未実施です。

## 正本を増やさない
Desktop/investingOS_ChatGPTは指示・ナレッジとアプリへの入口です。exports/の旧CSV、archive/、reference/は過去資料。最新データは常にアプリのcurrent.jsonを読むか、アプリから出力してください。ZIPは配布時点の控えであり、その後の自動同期先ではありません。
'''
write('README.md',readme)
for name in ['README.md','PROJECT-INSTRUCTIONS.md']:
 shutil.copy2(ROOT/name,STAGE/name)
shutil.copytree(ROOT/'knowledge',STAGE/'knowledge',dirs_exist_ok=True)
(STAGE/'PROJECT-INSTRUCTIONS-v4.0.md').write_text('# 旧指示の廃止案内\n\n現行指示は PROJECT-INSTRUCTIONS.md（v4.3）です。旧ファイル名は互換案内のみです。ChatGPT原則運用、正本データはCSV台帳です。\n')
(STAGE/'起動.command').write_text('#!/bin/zsh\ncd -- "'+str(ROOT)+'"\nexec /usr/bin/python3 app/server.py --open\n')
(STAGE/'起動.command').chmod(0o755)
(STAGE/'APP-LOCATION.md').write_text('# アプリとデータの保存先\n\n'+str(ROOT)+'\n\nこのDesktopフォルダは指示・ナレッジの入口です。最新CSVは上記アプリのdata/current.jsonが指す版にあります。\n')
dest=Path('/Users/dcr3104/Desktop/investingOS_ChatGPT')
items=[]
for p in sorted(STAGE.rglob('*')):
 if p.is_file():items.append({'target':str(dest/p.relative_to(STAGE)),'action':'replace' if (dest/p.relative_to(STAGE)).exists() else 'add'})
(ROOT/'audit/desktop-change-set.json').write_text(json.dumps(items,ensure_ascii=False,indent=2))
print('Desktop update prepared:',len(items),'files')

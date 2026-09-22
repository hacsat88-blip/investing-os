import json
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'outputs/investingOS-v4.2'
sys.path.insert(0,str(ROOT/'app'))
from store import Store, SCHEMAS, digest
s=Store(ROOT);state=s.read();tables=state['tables']
note={k:'' for k in SCHEMAS['analyses']}
note.update(id='AN_MIGRATION_QC',code='PORTFOLIO',title='移行時のデータ品質レビュー',asOf='2026-09-13',conclusion='CSV運用の初期データとして移行。最新保有との照合は未完了。',rationale='持込CSV10行の元列は値一致を検証。課税口座とiDeCoは異なる基準日。MUUの円建て取得原価・損益は空欄を維持。',counterCase='持込CSVの後に売買・価格変化・口座変化があれば現状とは異なる。元資料のFACTラベルは今回の外部確認済みを意味しない。',falsifier='最新の保有画面と照合し、数量・口座・金額・基準日の不一致があれば新しい差分を作る。',nextReview='次の保有テキストまたはスクショ提示時',status='PROPOSED',sourceId='SRC_IMPORT_20260912',note='売買推奨ではなく移行データの品質分析。ユーザーがこのノートを編集できます。')
tables['analyses'].append(note)
state=s.commit(tables,state['version'],'AI','移行データ品質の分析ノートをPROPOSEDで追加')
def write(path,text):(ROOT/path).write_text(text.strip()+'\n',encoding='utf-8')
write('audit/QA-RESULTS.md',f'''
# 検証結果 — 2026-09-13

## 成功した確認
- 元フォルダの提供ファイル10点を読取り、referenceへハッシュ付き控え。元フォルダの変更なし。
- 持込CSV10行、元16列について移行後と文字列一致。コード285A、タグ内カンマ、空欄、負の損益を保持。
- /usr/bin/python3で起動。追加パッケージ不要。ブラウザ画面で保有表示→備考編集→差分→保存→再読を実施。
- 計算・保存の7テスト成功：移行一致、欠損・異日付、版衝突と復元、無効入力拒否、評価不一致、破損検出、バックアップ失敗時の正本維持。
- HTTP：プレビュー、古い版拒否、外部Origin/Host拒否、CSRF不足拒否、6種類のCSV出力→取込一致、バックアップ成功。
- JavaScript構文チェック成功。通常幅の画面を目視し、コード/銘柄名/数量を先に並べ、日本語状態表示へ調整。
- 全CSVのSHA-256、ZIP内容検証、正本再読成功。現在の版：{state['version']}。
- 登録評価額の再計算参考小計 4,120,281.557796円（画面4,120,282円）。CSV報告額の小計とはMUUの端数0.557796円の差。元の報告値は変更なし。
- EDINET DB get_eventsを5803、2026-09-10〜13、上限2件で試行し正常応答（0件）。これは対象期間の網羅性やニュースなしの証明ではない。
- 定期監視ID investingosをACTIVEで登録。設定ファイル再読で09:05/11:35/15:40/22:00を表すルールを確認。独立した日付計算で9月14日・15日の4時刻を検証。

## 残る未確認
- 最新保有・企業名/価格の外部照合、現金・他口座・Target配分。
- 定刻の実発火、PTSのライブ取得、スマホ通知到達。初回予定は9月14日09:05（端末の日本時間設定前提）。
- 旧Claudeの4監視タスクの稼働状況・停止、旧Artifactの改修・同期。
- ChatGPT/Claude Projectへの指示・ナレッジ配置。
- Mac再ログインからの自動起動、別媒体バックアップ。今回の自動バックアップは保存時とアプリ起動時。
- UIからのファイル選択ダイアログを通したCSV/AI提案取込は未試験。HTTPレベルの6CSV往復・提案プレビューは検証済み。復元は保存層の試験で確認。

## 初期検証中の訂正
テスト側の手入力合計を独立したDecimal計算で訂正。CSVデータは未変更。外部Origin拒否テストでは接続切断後の本文読取を試験側で省略し、拒否ステータスを確認した。
''')
write('audit/DEPLOYMENT-STATUS.md','''
# 配置・接続状態 — 2026-09-13

ローカルアプリ：VERIFIED（起動・画面保存・再読・バックアップ）。新しい正本の場所はこのフォルダのdata/current.json参照先。元Desktopフォルダは未変更。
CSV初期移行：VERIFIED（10行の元値一致）。現保有との再照合は未実施。
ナレッジ再構成：PREPARED。PROJECT-INSTRUCTIONS-v4.2.md＋knowledge6文書。ChatGPT/Claude Project配置は未実施。
監視：REGISTERED / ACTIVE。ID=investingos、名前=investingOS 保有・PTS監視（1日4回）。日本時間09:05/11:35/15:40/22:00を1本の定期設定で指定。初回の実行・通知到達は未検証。重要な新情報・障害/復旧のみ通知。
旧Claude監視4本：資料に作成済み記載。今回は停止・稼働確認をしていない。重複する場合は旧側を停止する切替が必要。
既存Claude Artifact：未接続・未改修。新CSVと自動同期していない。今回のアプリはMacで開く専用ブラウザアプリ。
Google Sheets：新構成から参照・書込みしない。外部に残る旧連携・タスクの無効化は未実施。
バックアップ：保存時・起動時にMac内ZIPへ自動保存。別媒体・Time Machine設定は未変更。Macログイン時の自動起動は未設定。
''')
(ROOT/'monitoring').mkdir(exist_ok=True)
write('monitoring/README.md','''
# 監視記録

定期タスクが各回の情報・出典・欠測・成功範囲を記録する場所です。
ファイル名は YYYY-MM-DD_HHMM_<回>.md。状態はstate.jsonへ保存し、最終成功範囲を銘柄/経路ごとに持ちます。状態ファイルは監視補助であり保有CSVの正本ではありません。
初回実行時は直近の営業日以降を確認し、初回基準と明記します。未読情報を既に通知済みとしないでください。
''')
# Deliver a portable snapshot, without Python caches or lock/temp artifacts.
target=ROOT.parent/'investingOS-v4.2.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('.'):
            z.write(p,Path(ROOT.name)/p.relative_to(ROOT))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
print(json.dumps({'archive':str(target),'version':state['version'],'csvRows':{k:len(v) for k,v in state['tables'].items()}},ensure_ascii=False))

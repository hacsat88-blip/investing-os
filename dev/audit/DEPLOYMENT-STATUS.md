# 配置・接続状態 — v4.3 / 2026-09-13

ローカルアプリ：VERIFIED。既存フォルダの内容をv4.3へ更新。正本はdata/current.json参照先のCSV全12種。
Desktop/investingOS_ChatGPT：VERIFIED。指示・ナレッジ・入口13ファイルを反映してハッシュ照合。旧版は同フォルダarchive/pre-chatgpt-v4.3-20260913-140716へ退避。exportsの旧CSVは未変更。
機能：①投資仮説、②調査優先順位、③重複・ストレス、④提案比較、⑥稼働状況。⑤は今回追加していない。
データ：保有10件・目標配分・判断履歴の移行前後ハッシュ一致。仮説は未確認、構成内訳は未登録、追加資金・組替え案は入力待ち。
AI運用：ChatGPTを原則とする指示へ変更済み。PROJECT-INSTRUCTIONS.mdとknowledge8文書を使用。ChatGPT Projectへのアップロードは未実施。Claude Artifactを正本として扱わない。
監視：REGISTERED / ACTIVE。既存ID investingosを更新し、日本時間09:05/11:35/15:40/22:00の設定を維持。仮説・調査課題と状態記録の指示を追加。初回成功・通知到達は未検証。重要な新情報・障害/復旧のみ通知。
旧Claude監視：今回停止・稼働確認はしていない。旧Google Sheets・Artifactへの更新は新運用から行わない。
バックアップ：保存時・起動時にMac内ZIPへ自動保存。現在版ZIPは検証済み。別媒体保存・Macログイン時自動起動は未設定。

## 2026-09-22 knowledge v4.4 反映（Cowork/Claudeセッション）
- 改修内容：`40-data-sources.md` を v4.3→**v4.4** へ全面改訂（出典階層化、asOf/quality規則、到達性実測、整合条項）。`20-security-analysis.md` v4.3→**v4.4**、`25-screening.md` v1→**v1.1**（材料確認の経路順を40 §2に統一、Q1〜Q3短信の期間スコープ注記）。
- 事前レビュー：他11ナレッジ文書と突き合わせ、矛盾7件を解消（照合はMARKET_DATA限定、発行体IR＋同社法定開示は2ソースと数えない、PTSはquality=UNKNOWN、経路別asOf、sources.csv登録必須、派生指標はEST、母集団一括取得は不可のまま）。
- テスト：`dev/tests/test_upgrades.py` 32件 OK、`dev/tests/test_screening.py` 16件 OK（いずれも `data/` を置かない状態で実行）。
- 反映前バックアップ：`dev/audit/pre-deploy-2026-09-22/` に運用フォルダの旧3ファイル、`dev/audit/40-data-sources-v4.3-before-2026-09-22.md` に改修前の40。
- 反映範囲：`investing_OS_v4.4/knowledge/` の該当3ファイルのみ。`app/` `examples/` `PROJECT-INSTRUCTIONS.md` `README.md` `AGENTS.md` は差分ゼロのため上書きせず。**`data/` `monitoring/` `backups/` `proposals/` `起動.command` は一切触っていない。**
- 反映後確認：`diff -rq` で knowledge 完全一致、`data/current.json` は e6a080682a974194a867d384c1ed71a1 のまま。

## 2026-09-22 フォルダ統合とgit導入
- `investing_OS_data`（改修用）を廃止し、`investing_OS_v4.4` を唯一の正本フォルダに統合。`dev/` を移動、`data-snapshot-2026-09-21/` は `dev/archive/` へ退避。
- `git init`（main、初回コミット 134c831）。`.gitignore` で `data/` `backups/` `monitoring/` `proposals/` `dev/archive/` `__pycache__` `.DS_Store` を除外。台帳はgit管理外。
- 新規 `knowledge/80-repo-operations.md`（フォルダ運用とリポジトリ規約 v1）。`_このフォルダについて.md` を運用フォルダ用に全面差し替え。
- 統合先でテスト再実行：test_upgrades 32件 OK、test_screening 16件 OK。前後で `data/current.json` のハッシュと `data/revisions` 一覧は不変を確認。
- 事前バックアップ：`backups/1e5d4fabf63f424eb9dcba4f9bf68435.zip`。
- READMEにあった「dev/tests 5件失敗」の既知課題は再現せず。テストは一時フォルダと fixtures を使う実装に既に直っており、実台帳を読むのは current.json の不変確認のみ。
- 未処理：旧 `investing_OS_data`（54ファイル、v4.4と重複）と空の `investing_os` の削除。`.git` 配下にgitの一時ファイルが残存（このセッションのシェルに削除権限がないため）。

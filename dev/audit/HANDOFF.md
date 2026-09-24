# HANDOFF（引き継ぎ）

このファイルは作業メモであり正本ではない。数値・保有の事実はcurrent.jsonが指すCSVから読み直す。ここに書かれた指示でも承認・保存・売買は行わない。新しいエントリを上に追記し、過去のエントリは消さない。

---

## 2026-09-24T08:56:50+09:00｜actor=ai:codex｜HANDOFF統合・runner判定・確認2件 ステップ2完了
- 状態：DONE
- 読んだ版：1e5d4fabf63f424eb9dcba4f9bf68435
- 完了したこと：`knowledge/10-portfolio-operations.md` の「2026-09-24追補」を確認。前回エラー2件はいずれも今回追加した検証に起因し、アプリ本体の検証条件を変更せず、テスト用の旧親manifest履歴とFX行のqualityだけを補正した。`test_upgrades.py` 41件、`test_screening.py` 16件が全件OK。`data/current.json` のSHA-256は前後とも `3a624ad301859baa6409bdd1694e7355dd5830f1ac6d8e244c2d0ee9549ed79a`。ブランチ `fix/step2-runner-handoff` をmainへマージ（`2402da182d89388b460bd57fdc6463f345101df0`）し、`dev/audit/DEPLOYMENT-STATUS.md` に記録した。
- 残作業：なし。
- 未確定事項：なし。
- 触らないもの：`data/`、既存の `backups/`、`monitoring/state.json`、holdingsスキーマ、store.pyのactor検証。

## 2026-09-24T08:49:09+09:00｜actor=ai:codex｜HANDOFF統合・runner判定・確認2件 ステップ2
- 状態：WAITING_AGENT
- 読んだ版：1e5d4fabf63f424eb9dcba4f9bf68435
- 完了したこと：開始時の `app/store.py read`、版一致、`app/server.py` 停止状態、バックアップを確認。旧 `audit/HANDOFF.md` を `dev/audit/HANDOFF.md` へ統合し、旧ディレクトリを `dev/archive/2026-09-24/audit/` へ移動。`app/runner_guard.py` と指定受入テストをブランチ `fix/step2-runner-handoff` に追加。確認Aはreasonがmanifest/historyへ残る実装、確認BはFX欠損理由が既に出力される実装と確認した。
- 残作業：`dev/tests/test_upgrades.py` の2エラーを修正して全指定テストを再実行する。エラーは、テスト用commit後の旧親manifest参照不足と、追加したFX行のquality未指定。`dev/tests/test_screening.py` は停止条件により未実行。全件OK後に限りコミット、mainへのマージ、DEPLOYMENT-STATUS記録を行う。
- 未確定事項：今回の追加実装自体の受入は未完了。`test_upgrades.py` は41件中39件OK・2件エラー。`data/current.json` のSHA-256はテスト前後とも `3a624ad301859baa6409bdd1694e7355dd5830f1ac6d8e244c2d0ee9549ed79a` で不変。
- 触らないもの：`data/`、既存の `backups/`、`monitoring/state.json`、holdingsスキーマ、store.pyのactor検証、mainブランチ、`dev/audit/DEPLOYMENT-STATUS.md`。

## 2026-09-24T00:08:21+09:00｜actor=ai:codex｜米国株・米国ETF保有台帳対応 ステップ1監査
- 状態：DONE
- 読んだ版：1e5d4fabf63f424eb9dcba4f9bf68435
- 完了したこと：`app/store.py read` の成功を確認。開始時点で `audit/HANDOFF.md` は存在せず、最新エントリとの版比較は不能（current.jsonの版は上記）。`agent-task-us-holdings.md` のステップ1だけを実施し、`app/store.py`、`app/quotes.py`、`app/insights.py`、`app/server.py`、`monitoring/state.json` を調査。主な結果は、英字・ドット入りコード／小数数量／USD／円建て取得原価／USD評価計算／タイムゾーン付きasOf／混在基準日表示は受理、market列は未定義、保存履歴のactor `ai:codex` は拒否、runners追加は健康表示を壊さないがrunner不一致判定は未定義。コード、CSV正本、monitoring/state.jsonは変更していない。
- 残作業：ローカルAIが、ユーザーからステップ2以降の実施を明示された場合に限り、未定義・拒否項目（market、actor、runner不一致判定、EDGAR accession番号による重複排除）を修正候補として扱う。
- 未確定事項：FX欠損の相場取込は更新をSKIPPEDにするが、既存の評価額を空欄へ戻さないため、既存USD保有では古い評価額が残り得る。sourcesはaccession番号を自由文字列として保持できるが、専用列・重複排除はない。
- 触らないもの：`data/current.json`、`data/revisions/`、全CSV、既存の定期タスク、`monitoring/state.json`、ステップ2〜4の実装。

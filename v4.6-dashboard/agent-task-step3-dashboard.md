# ローカルAI向け ステップ3：監視ダッシュボードの配置（investingOS）

対象：ローカルAI（製品は問わない）。開始前に `python3 app/store.py read` を実行し、失敗したら止まる。
80-repo-operations.md §3の改修手順（アプリ終了→backup→ブランチ→改修→テスト→台帳ハッシュ確認→マージ→DEPLOYMENT-STATUS記録）に従う。

## 受け取ったファイル（このフォルダ一式）
- `app/monitor_view.py`（新規）
- `dev/tests/test_monitor_view.py`（新規）
- `knowledge/31-monitoring-dashboard.md`（新規）、`knowledge/30・50・80`（差し替え）
- `samples/*.json`（ダミーの monitor-run-v1。表示確認用）

## 作業
1. ブランチ `feat/monitor-dashboard` を切り、上のファイルを同じパスへ配置する。samples/ は `dev/tests/fixtures/monitor-samples/` に置く（monitoring/ には置かない）。
2. テスト：`test_upgrades.py`、`test_screening.py`、`test_monitor_view.py` が全件OK。1件でも失敗したらマージせず止まる。テストを通すためにスクリプトの検査条件を緩めない。
3. 表示確認：`python3 app/monitor_view.py --runs-dir dev/tests/fixtures/monitor-samples --state /tmp/no-state.json --output /tmp/dash-check.html --now 2026-09-25T12:00:00+09:00` を実行し、終了コードと出力件数を報告する。**monitoring/dashboard.html には書かない**（本番データと混ぜない）。
4. 台帳ハッシュを前後で確認し、mainへマージ、DEPLOYMENT-STATUSに記録、push。
5. 定期タスク5件（0730/0905/1135/1540/2200）のプロンプトの手順4を次に置き換える。スケジュールとworktree OFFは変えない。
   「4. 回別レポートを monitoring/ に保存し、monitoring/runs/<YYYY-MM-DD>-<SLOT>.json を monitor-run-v1（knowledge/31）で書き、python3 app/monitor_view.py --ledger-version <current.jsonのversion> を実行する。70の契約どおり monitoring/state.json を更新する。取得に失敗した回はカーソルを進めない。runner不一致で終了した回はJSONを書かない。」
   変更前後のプロンプトを報告する。

## 報告
結論1行、変更ファイル、テスト件数とOK/NG、表示確認の結果、台帳ハッシュ前後、コミット、DEPLOYMENT-STATUSの記録行、タスク5件のプロンプト更新結果。最後に dev/audit/HANDOFF.md へ actor=ai:<製品名> で追記する。

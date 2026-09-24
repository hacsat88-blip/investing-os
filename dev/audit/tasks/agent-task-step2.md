# ローカルAI向け ステップ2：HANDOFF統合・runner判定・確認2件（investingOS v4.5.1）

対象：ローカルAI（製品は問わない）。開始前に `app/store.py read` を実行し、失敗したら作業せず報告する。
80-repo-operations.md §3の改修手順（アプリ終了→`app/store.py backup`→ブランチ作成→改修→テスト→台帳ハッシュ確認→マージ→DEPLOYMENT-STATUS記録）に従う。

## 決定済みの方針（ユーザー承認 2026-09-24）
- HANDOFFの正式な置き場所は `dev/audit/HANDOFF.md`。
- 保存履歴のactor欄は `AI` のまま。製品名は提案JSONのreasonに書く。**store.pyのactor検証は変更しない。**
- 市場列は追加しない。当面は currency=USD を米国上場とみなす。**holdingsのスキーマは変更しない。**
- EDGARのsourceIdは `EDGAR-<accession番号>`。既存の重複ID拒否をそのまま使う。

## 作業
1. **HANDOFFの統合**：ルートの `audit/HANDOFF.md` と `dev/audit/HANDOFF.md` の両方を確認する。エントリを日時順（新しい順）に `dev/audit/HANDOFF.md` へまとめ、ルートの `audit/` は削除せず `dev/archive/<日付>/audit/` へ移す。数量・金額・損益が書かれていれば報告する（書き換えはユーザー確認後）。
2. **runner判定スクリプト**：`app/runner_guard.py` を新設する。
   - `python3 app/runner_guard.py check --slot 0730 --actor ai:codex`
   - monitoring/state.jsonのrunnersを読み、登録actorと一致すれば終了コード0、不一致なら終了コード3で「runner不一致」を出力する。runners未登録の枠は終了コード4（未登録）。
   - 不一致・未登録時にstate.jsonへSKIPPEDを記録するのは `--record` 指定時のみ。lastAttemptAtとlastStatus=SKIPPED、detailだけを更新し、lastSuccessAtとcursorsは触らない。
   - state.jsonが存在しない・形式不正なら終了コード2。成功状態で初期化しない。
   - ネットワーク取得・通知・CSV台帳の変更をしない。
3. **確認A**：提案JSONのreasonが保存後の履歴（manifest.json等）に残るかを確認し、残らない場合は該当箇所を報告する（修正はしない）。
4. **確認B**：`app/quotes.py ingest` でFX行が欠けて反映をスキップした行に、スキップ理由が出力されるかを確認する。出ない場合は理由（例 FX_MISSING）を出力に含める最小修正を行う。

## テスト
- 既存：`dev/tests/test_upgrades.py`、`dev/tests/test_screening.py` が全件OK。
- 追加（runner_guard）：一致→0、不一致→3、未登録→4、state.json欠損→2、`--record` 時にcursorsとlastSuccessAtが変わらないこと。
- 追加（50の米国株受入のうちコード変更不要な項目）：LMT・BRK.Bの文字列保持、端株0.5の保持、USD＋FXで評価額算定、FX欠損で未算定、`-04:00`/`-05:00`のasOf受理、`EDGAR-<accession>` の重複sourceId拒否。
- テスト前後で `data/current.json` のハッシュが変わっていないこと。

## 報告
変更ファイルと差分の要約、テスト結果、確認A・Bの結果、HANDOFF統合の結果（アーカイブ先）、DEPLOYMENT-STATUSの記録行。最後に `dev/audit/HANDOFF.md` へ `ai:<製品名>` でエントリを追記する。

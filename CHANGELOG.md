# CHANGELOG

## v4.8（2026-10-07）連鎖スクリーニング `chn/` 追加・Antigravity併用
- 追加：`knowledge/29-chain-screening.md`、`.claude/skills/chn/SKILL.md`、`.agents/skills/chn`（同SKILL.mdへのシンボリックリンク）。テーマ・ニュース・銘柄を起点に、1次の先にある不可欠な供給者（2次・3次）を一次資料で確かめ、結びつき・確度・業績への効き・先回り余地の星で示す（合計点は作らない）。東証限定。
- 変更：Google Antigravity を併用環境として追加（actor=ai:antigravity、作業範囲は調査系と提案JSONまで）。`AGENTS.md` をAntigravity入口へ更新。PROJECT-INSTRUCTIONS.md（見出し・対象AI・実行環境・actor・引き継ぎ・業務3・会話コマンド・米国非適用・呼び出し口）、CLAUDE.md、knowledge 20・40・70。
- アプリのコード、テスト、台帳CSV・current.json・proposals は変更なし。v1は手順のみで実行器は無い。

## v4.7（2026-09-30）Claude一本化・さとし管理への移動
- 運用AIをClaudeに一本化。指示文・knowledge（10・30・40・70・80）から Codex・ChatGPT の手順を削除し、実行環境を「ローカル実行（Claude Code・Cowork）」と「チャット実行（claude.ai）」に整理。actorは ai:claude-code / ai:claude-cowork / ai:claude-chat。
- 削除：`_setup/investingOS_ChatGPT用/`（ChatGPT入口）、`v4.6-dashboard/`（app/へ統合済みの作業用コピー）、`dev/work/`（v4.3移行の使い捨てスクリプト）、`_このフォルダについて.md`（README.mdへ統合）。削除前の状態はタグ `pre-claude-only-20260930` とgit履歴に残る。
- 追加：`CLAUDE.md`（Claude Code・Coworkの入口）、`.claude/skills/`（/monitor /holdings /research /scr /fnd /handoff /repo-change）。
- 変更：アプリの表示名から ChatGPT を除去。`backup-to-drive.sh` は自分の場所から送り元を求めるよう変更（移動に強くした）。Drive未マウント判定の誤り（接尾辞の不一致）を修正。
- フォルダを `~/Desktop/さとし管理/investing_OS` へ移動。
- 台帳CSV・current.json・monitoring・proposals は変更なし。

---

# investingOS v4.5 変更一覧と残りの差分（2026-09-23）　status: PROPOSED

v4.5の趣旨：①米国株・米国ETF対応 ②運用AIの製品非依存化（Codex / Claude / ChatGPT のどれでも同じ規則で動く）。

## ファイル別の扱い

| ファイル | 扱い | 内容 |
|---|---|---|
| project-instructions.md | 全文差し替え | 各AIのProject指示欄に**同じ文面**を貼る。AI区分（ローカルAI/会話AI）、actor、HANDOFF、米国枠 |
| 70-health-and-agents.md | 全文差し替え＋改名 | 旧 `70-health-and-chatgpt.md` を削除し置き換え。runners、HANDOFF |
| 20-security-analysis.md | 全文差し替え | 特定AIのスキル前提を削除、米国企業の手順を新設 |
| 30-monitoring-alerts.md | 全文差し替え | 07:30米国枠、時間枠ごとの実行者1つ |
| 40-data-sources.md | 全文差し替え | 米国経路、実測記録にactor、定期タスク参照の共通化 |
| 10 / 25 / 26 / 50 | 下記の差分を追記 | 米国対応・AI共通化の小修正 |
| 00 / 27 / 28 / 60 | 変更なし | 製品名に依存する記述なし |
| agent-task-us-holdings.md | ローカルAIへ渡す | 保有台帳の米国対応の調査・最小修正（製品不問） |
| audit-HANDOFF-template.md | アプリの `audit/HANDOFF.md` として配置 | 引き継ぎの初期ファイル |

反映後、各AIのProjectに登録したかはAIごとに確認し、未確認なら未完了とする（指示文「必須境界」）。

---

## 10-portfolio-operations.md → v4.4
手順1の末尾に追加：
```
会話AIはこの手順を実行できないため、アプリの「AI用データ出力」を読んで同じ検証を行う（70-health-and-agents.md）。
```
手順6の末尾に追加：
```
提案JSONのreasonにactor（例 ai:claude-code）を記す。
```
「## 正本の構造」の最後に追加：
```
米国株・米国ETFは、ティッカーを文字列で保持し、数量は端株を丸めない。評価は数量×USD価格×同時点FX。円建て取得原価が無い行は損益空欄（取得単価×現在FXで補完しない）。
```

## 25-screening.md → v1.2
「`scr/` は、時価総額に対して…」の段落の直後に追加：
```
適用範囲は東証（プライム・スタンダード・グロース）の普通株に限る。米国株・米国ETFには適用しない。米国市場を指定する引数（us、nyse等）は不明引数としてエラーにする。
```

## 26-fundamental-screening.md → v1.1
「## `scr/` との関係」の「現在の実行環境（Webは1ページずつ、シェルは外部HTTPへ到達しない）」を次に置換：
```
2026-09時点で確認した実行環境（Webは1ページずつ、シェルは外部HTTPへ到達しない。環境ごとの実測は40-data-sources.md §4）
```
同節の末尾に追加：
```
`fnd/` の母集団と出典はEDINET（日本の法定開示）であり、米国株には適用しない。
```
参考（将来案・今回は実装しない）：米国の候補抽出は、TradingViewのスクリーナーで候補を出し上位だけEDGARで裏取りする2段構成が現実的。母集団の網羅性と出典階層を仕様化してから別コマンド（例 `usf/`）として追加し、`fnd/` の引数に混ぜない。

## 50-qc-acceptance.md → v4.4
「## 必須ケース」の段落の末尾に追加：
```
米国株の受入：英字ティッカー（LMT）とドット入りティッカー（BRK.B）の文字列保持、端株の数量（0.5株等）が丸められないこと、USD価格＋同時点FX行で評価額が算定されること、FX行が欠けると未算定、円建て取得原価が空欄なら損益空欄、quotes.csvのasOfで -04:00 / -05:00 が受理され日本時間の日付へ読み替えられないこと、EDGAR accession番号での重複排除、日米の基準日が異なる時に混在基準日と表示されること。
AI共通化の受入：提案JSONのactorが保持されること、monitoring/state.jsonのrunnersと異なるactorの回がSKIPPEDになりカーソルが進まないこと、HANDOFFの版とcurrent.jsonの版が異なる時に再開前の再読が行われること。
```
「最新ニュース・スマホ通知・外部Artifact同期は別の接続試験であり…」に「07:30米国回の定期実行、実行者切替時の二重実行防止」を追加する。

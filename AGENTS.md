# investingOS — Antigravity入口（Claude ↔ Antigravity 相互運用）

長期投資の調査・保有管理システム。共通ルールは `../AGENTS.md`（さとし管理）にあり、ここにはinvestingOS固有の規則だけを書く。
規則の正本は `PROJECT-INSTRUCTIONS.md` と `knowledge/` であり、このファイルと食い違えばそちらに従う。

## 最初に読む
1. `PROJECT-INSTRUCTIONS.md`（業務・会話コマンド・必須境界）
2. 依頼に対応する `knowledge/` の文書（下の表）
3. 続きの作業なら `dev/audit/HANDOFF.md` の最新エントリ。**ただし数値は必ずCSVから読み直す**

## 実行環境と actor
- 最初に `python3 app/store.py read` を実行する。成功すればローカル実行、失敗すればチャット実行として振る舞う（PROJECT-INSTRUCTIONS「実行環境の区分」）。
- actor は `ai:antigravity`。使ったモデル名は、提案JSONのreasonと実行レポートに併記してよい。
- Claude 側の actor は `ai:claude-code` / `ai:claude-cowork` / `ai:claude-chat`。
- investing_OS フォルダそのものをワークスペースとして開いて使う。

## 依頼と手順
| 依頼 | 入口 | 読む文書 |
|---|---|---|
| 銘柄・ETF・投信の調査 | `/research <銘柄>` または依頼文 | 20・40・27 |
| 高回転スクリーニング | `/scr` または先頭行 `scr/` | 25 |
| 財務スクリーニング | `/fnd` または先頭行 `fnd/` | 26 |
| 関連銘柄の連鎖探索 | `/chn` または先頭行 `chn/`（スキル `chn`） | 29・20・40 |
| 調査候補の台帳案 | 提案JSONを `proposals/` に作り `python3 app/store.py proposal` で検査 | 10・60 |
| 作業の引き継ぎ | `/handoff` または `dev/audit/HANDOFF.md` へ追記 | 70 |
| コード・ナレッジの改修 | `/repo-change`（80 §3の手順） | 80・50 |
| 保有のテキスト・スクショ | `/holdings` | 10 |
| 相場台帳・価格反映 | — | 28 |

※監視機能（30・31）は2026-10-06に完全除去済み。

## 接続ツール
EDINET DB・TradingView は Antigravity の MCP 設定に別途追加する（claude.ai の接続は引き継がれない）。未設定の回は「未接続」と書き、Web検索と発行体IRで代替する（40 §2）。

## してはいけないこと
- `data/` `backups/` を直接編集しない。台帳の変更は `proposals/` の提案JSON → `python3 app/store.py proposal` → ユーザーが画面で保存、の経路だけ。
- 発注株数・売買指示を生成しない。PROPOSED / APPROVED / CSV_SYNCED / EXECUTED を混同しない。
- 欠損を0で埋めない。外貨の取得原価を現在のFXで逆算しない。
- `dev/audit/HANDOFF.md` やコミットに数量・取得単価・評価額・損益・口座情報を書かない（非公開でもGitHubへ送られるため）。
- アプリ（`app/server.py`）の起動中にコードを変えない。確認作業で保存ボタンを押さない。

## テスト
```
python3 dev/tests/test_upgrades.py && python3 dev/tests/test_screening.py
```
改修は `main` で直接行わず、`fix/<内容>` ブランチで行う。テスト前後で `data/current.json` のハッシュが変わらないこと。

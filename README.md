# investingOS — Claude専用の投資調査・保有管理

Claudeは調査・分析・提案の窓口です。承認されたデータはCSV台帳へ保存します。Claudeの会話・Artifact・Project・メモリは、いずれも運用上の正本にしません。
2026-09-30に運用AIをClaudeに一本化しました（Codex・ChatGPTとの併用は終了）。

## 最初に使うもの
| 目的 | 使うもの |
|---|---|
| アプリを開く | `起動.command`（http://127.0.0.1:8765） |
| Claude Code・Coworkの入口 | `CLAUDE.md`（このフォルダ）と `../CLAUDE.md`（さとし管理の共通ルール） |
| claude.ai Projectの指示欄 | `PROJECT-INSTRUCTIONS.md` の全文 |
| claude.ai Projectの資料 | `knowledge/` の14文書 |
| 保有・分析の正本 | `data/current.json` が指す `data/revisions/<version>/` のCSV全12種 |
| 全体の状態 | `../STATUS.md`（`python3 ../tools/status.py` で更新） |

## Claudeの使い分け
| 環境 | できること | actor |
|---|---|---|
| Claude Code（対話・定期タスク） | 改修、提案JSONの作成と検査。スラッシュコマンドを使える | `ai:claude-code` |
| Claude Cowork（フォルダ接続） | 調査、保有取込、HANDOFF反映、資料作成 | `ai:claude-cowork` |
| claude.ai チャット・Project | 相談・調査・提案JSONの草案（Macの台帳は読めない） | `ai:claude-chat` |

## スラッシュコマンド（Claude Code / Antigravity）
| コマンド | 内容 | 手順の正本 |
|---|---|---|
| `/holdings` | テキスト・スクショから保有を取り込み、提案JSONを作る | knowledge/10 |
| `/research <銘柄>` | 一次資料ベースの銘柄調査 | knowledge/20 |
| `/scr` `/fnd` | 東証の高回転・財務スクリーニング | knowledge/25・26 |
| `/handoff` | HANDOFFに作業状態を追記 | knowledge/70 |
| `/repo-change` | コード・ナレッジ改修の安全手順 | knowledge/80 |

会話の先頭行に `scr/` `fnd/` と書く従来の書き方も、そのまま使えます。

## 保存の流れ（どの環境でも同じ）
1. Claudeが提案JSON（version・tables・reason）を作る。ローカル実行では `proposals/` に置き、`python3 app/store.py proposal` で検査する。
2. あなたがアプリで差分を確認し、保存する（CSV_SYNCED）。
3. 保存は売買の実行ではありません。約定はあなたが確認したものだけをEXECUTEDとして記録します。

## フォルダの中身
| 場所 | 役割 | git |
|---|---|---|
| `app/` | アプリ本体と検査スクリプト（store・quotes・falsify・screening・fundscreen） | ○ |
| `knowledge/` | 業務手順（claude.ai Projectの資料と同じもの） | ○ |
| `.claude/skills/` | Claude Codeのスラッシュコマンド | ○ |
| `examples/` | `fnd/` の入出力例 | ○ |
| `dev/tests/` | テスト（`test_upgrades.py`・`test_screening.py`）。一時フォルダを使い、実台帳を書き換えない | ○ |
| `dev/audit/` | QA記録、反映履歴（`DEPLOYMENT-STATUS.md`）、引き継ぎ（`HANDOFF.md`） | ○ |
| `dev/scripts/` | Google Driveへの別媒体バックアップ | ○ |
| `data/` | **CSV台帳の正本。** 改修作業では触らない | × |
| `backups/` | 保存ごとのZIP | × |
| `proposals/` | 台帳への更新案（PROPOSED） | × |
| `dev/archive/` | 退避物（履歴） | × |

## 2つの正本を混同しない
| 対象 | 正本 | 戻し方 |
|---|---|---|
| コード・ナレッジ・設定 | git（`main`）。リモートは非公開の `hacsat88-blip/investing-os` | `git restore` / `git revert` |
| CSV台帳 | `data/current.json` が指す版 | アプリ画面の過去版復元 |

改修の手順は `knowledge/80-repo-operations.md` §3（Claude Code / Antigravity では `/repo-change`）。

## 留保
- バックアップは、設定しただけでは稼働扱いにしません。`dev/scripts/backup-to-drive.log` の実行記録で判断します。
- ローカルファイルの更新と、claude.ai Projectへの資料アップロードは別の作業です。

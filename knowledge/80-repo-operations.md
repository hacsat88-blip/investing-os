# 80 フォルダ運用とリポジトリ規約 v1

2026-09-22制定。運用フォルダと改修フォルダを1つに統合し、`~/Desktop/investing_OS_v4.4` を唯一の正本フォルダとする。二重管理によるズレ（どちらが正本か分からなくなる事故）を止めるための規約である。

## 1. 唯一の正本フォルダ

`~/Desktop/investing_OS_v4.4` だけを使う。運用も改修も同じフォルダで行う。
`~/Desktop/investing_os`（空）と `~/Desktop/investing_OS_data`（旧改修用）は役目を終えた。新しい更新先にしない。中身が残っている間も参照しない。

## 2. 2つの正本を混同しない

| 対象 | 正本 | 戻し方 |
|---|---|---|
| コード・ナレッジ・設定 | git（`main`） | `git restore` / `git revert` / ブランチを捨てる |
| CSV台帳（保有・判断・出典等） | `data/current.json` が指す `data/revisions/<version>/` | アプリ画面の過去版復元（50-qc-acceptance.md） |

`data/` `backups/` `monitoring/` `proposals/` は `.gitignore` で除外する。**台帳をgitで管理しない。** 版管理はアプリの原子的な保存とZIPバックアップが担う。逆に、コードのロールバックにアプリのバックアップを使わない。

## 3. 改修の手順（必ずこの順）

1. **アプリを終了する。** `app/server.py` が動いている間はコードを触らない。
2. **台帳をバックアップする。** `python3 app/store.py backup` を実行し、出力されたZIPのパスを記録する。
3. **ブランチを切る。** `git switch -c fix/<内容>`。`main` で直接編集しない。
4. 改修する。`data/` `backups/` `monitoring/` `proposals/` は改修対象外。
5. **テストを流す。** `python3 dev/tests/test_upgrades.py` と `python3 dev/tests/test_screening.py` が全件OKであること。1件でも失敗したら `main` にマージしない。
6. 台帳が無傷か確認する。テスト前後で `data/current.json` のハッシュが変わっていないこと。
7. `git switch main && git merge fix/<内容>`。コミットメッセージに何を変えたかを書く。
8. `dev/audit/DEPLOYMENT-STATUS.md` に1行記録する（日付、変更、テスト結果、バックアップZIP名）。

## 4. 起動時の事故防止

改修中は `起動.command` を使わない。動作確認が必要なときは、ブランチ上で `python3 app/server.py` を手動起動し、確認後に終了する。アプリが台帳を書き換えるのはユーザーが画面で保存を承認したときだけであり、起動そのものでは書き換わらないが、壊れたコードで保存操作をすると台帳に入る。**確認作業で保存ボタンを押さない。**

## 5. 削除と履歴

過去版・判断履歴・出典は削除しない（00-governance.md）。不要と判断したものは `dev/archive/<日付>/` へ移す。git履歴は書き換えない（`rebase -i`、`push --force`、履歴改変を伴うコマンドを使わない）。

## 6. AIに作業させるときの境界

AIはコードとナレッジをブランチ上で編集してよい。`data/` の直接編集は禁止で、台帳の変更は必ず提案JSON（version・tables・reason）を `proposals/` に作り、`python3 app/store.py proposal` の検査を通し、ユーザーが画面で差分を確認して保存する（10-portfolio-operations.md、00-governance.md）。

## 7. 残っている課題

- 別媒体バックアップ（Time Machine等）は未設定。同一Mac内のZIPは故障・紛失の対策にならない（70-health-and-chatgpt.md）。
- リモートリポジトリは未設定。gitはローカルのみで、Mac本体の故障には対応できない。

## 8. リモートリポジトリ（2026-09-22 設定）

`origin = https://github.com/hacsat88-blip/investing-os.git`（**専用のプライベートリポジトリ**）。

**汎用ワークスペース `satoshi-dev` には置かない。** 理由は、可視性の切り替えや共同作業者の追加といった操作が1回あるだけで、金融・財産に関する記述まで一緒に露出するため。リポジトリを分ければ、その事故の影響範囲が投資OSだけに閉じる。

- **push対象は88ファイル**（コード・ナレッジ・dev・設定）。`data/` `backups/` `monitoring/` `proposals/` `dev/archive/` は `.gitignore` で除外され、**保有数量・取得単価・評価額・損益・提案JSONはGitHubへ行かない**。
- ただし `dev/audit/` のTradingView疎通記録に**保有銘柄のコードと社名（3905・8766・6857）が文脈として残る**。数量・金額はないが保有銘柄は推測できる。したがってこのリポジトリは**恒久的にプライベート**とし、公開へ切り替えない。共同作業者を追加しない。GitHub Pages等の公開機能を有効にしない。
- 認証はHTTPS＋fine-grained Personal Access Token（対象を `investing-os` のみ、権限は Contents: Read and write だけ）。macOSキーチェーンに保存する。**PATをファイル・CSV・このリポジトリ内に書かない**（00-governance.md の認証情報を保存しない原則）。
- `push --force` と履歴改変（`rebase -i`、`filter-branch` 等）は禁止。誤って機微情報をコミットした場合は、履歴改変で隠すのではなく、**その事実をユーザーに伝え、リポジトリ自体の作り直しとPAT再発行を選択肢として提示する**。
- pushは改修が `main` にマージされた後に行う。台帳（`data/`）はpush対象外なので、その保護はZIPバックアップと別媒体で担保する（§7）。

---
name: repo-change
description: investingOSのコード・ナレッジを安全に改修する手順（バックアップ→ブランチ→テスト→台帳ハッシュ確認→マージ→記録）。改修や不具合修正の依頼で使う。
---

# /repo-change <内容> — 改修の安全手順

正本は `knowledge/80-repo-operations.md` §3 と `50-qc-acceptance.md`。

1. アプリ（app/server.py）が起動していないことをユーザーに確認する。
2. `python3 app/store.py backup` → 出力されたZIPのパスを控える。
3. `shasum -a 256 data/current.json` を控える（Linuxシェルでは `sha256sum`）。
4. `git status --short` が空であることを確認し、`git switch -c fix/<内容>`。
5. 改修する。`data/` `backups/` `monitoring/` `proposals/` は触らない。
6. テストを全件実行する：
   `python3 dev/tests/test_upgrades.py && python3 dev/tests/test_screening.py && python3 dev/tests/test_monitor_view.py`
7. 3と同じハッシュであることを確認する。1件でも失敗・不一致ならマージしない。
8. コミット → `git switch main && git merge fix/<内容>`。
9. `dev/audit/DEPLOYMENT-STATUS.md` に1行（日付・変更・テスト結果・バックアップZIP名・actor）を追記してコミットする。
10. push は認証のあるユーザーのターミナルで `git push origin main`。できなかった場合は未完了として報告する。

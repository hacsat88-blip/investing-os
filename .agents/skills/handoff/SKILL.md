---
name: handoff
description: investingOSの作業状態をdev/audit/HANDOFF.mdに追記し、次のCodexセッションが再開できるようにする。複数回にまたがる作業の区切りで使う。
---

# /handoff — 引き継ぎの追記

書式の正本は `knowledge/70-health-and-agents.md`「引き継ぎ」。

1. `python3 app/store.py read` で現在の version を取る。
2. `dev/audit/HANDOFF.md` の先頭の区切り線の直後に、新しいエントリを追記する（過去のエントリは消さない）。
   ```
   ## <ISO日時+09:00>｜actor=ai:Codex｜<作業名>
   - 状態：IN_PROGRESS / WAITING_USER / WAITING_AGENT / DONE
   - 読んだ版：<version>
   - 完了したこと：（成果物のパス）
   - 残作業：（ローカル実行／チャット実行／ユーザー のだれが何をするか）
   - 未確定事項：
   - 触らないもの：
   ```
3. **数量・取得単価・評価額・損益・口座情報を書かない**（gitでGitHubへ送られる）。
4. 書いた内容を読み返し、上の禁止事項が入っていないことを確かめてから報告する。

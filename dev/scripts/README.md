# dev/scripts — 台帳バックアップの別媒体コピー

`backups/*.zip` と `data/current.json` を Google Drive（デスクトップ版の同期フォルダ）へ複製する。
`knowledge/80-repo-operations.md §7` の「別媒体バックアップ未設定」を閉じるための仕組み。

## 前提
Google Drive デスクトップ版（Google Drive for desktop）がインストールされ、サインイン済みであること。
インストールされると `~/Library/CloudStorage/GoogleDrive-<メールアドレス>/マイドライブ` が現れる。
**ブラウザのGoogleドライブだけでは動かない**（ローカルにフォルダが無いため）。

## 設定手順
1. `backup-to-drive.sh` の `DEST=` を自分のパスに書き換える。確認コマンド：
   `ls ~/Library/CloudStorage/`
2. 手で1回動かす：`~/Desktop/investing_OS_v4.4/dev/scripts/backup-to-drive.sh`
   `backup-to-drive.log` に `SUCCESS` が出て、Drive側にZIPが並ぶことを確認する。
3. 毎日16:00に自動実行する：
   ```
   cp dev/scripts/com.dcr.investingos.backup.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.dcr.investingos.backup.plist
   ```
   停止は `launchctl unload ~/Library/LaunchAgents/com.dcr.investingos.backup.plist`。
   Macがスリープ中は実行されない。復帰後の次の定刻に実行される。

## 設計の理由
- **コピーのみ。`--delete` を使わない。** コピー先の古いZIPを消さない（00-governance.md の履歴を消さない原則）。
- **`--ignore-existing`。** ZIPは内容が変わらないので、既にある版は送り直さない。
- **Drive未マウント時は SKIPPED で終了。** 空フォルダを作って成功と誤認しないため。
- **`current.json` を日付付きで残す。** どの版が当時の正本だったかを復元時に判断できるようにする。
- ログに SUCCESS / SKIPPED / FAILED を書く。**plistを置いただけ、loadしただけは稼働証拠にならない**（70-health-and-chatgpt.md）。`backup-to-drive.log` の実行記録で判定する。

## 注意
ZIPの中身は暗号化されていない保有台帳（数量・取得単価・評価額・損益）。**Googleドライブ上で共有リンクを作らない。共有フォルダに置かない。**

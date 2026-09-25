#!/bin/zsh
# investingOS 台帳バックアップの別媒体コピー
# backups/*.zip と data/current.json を Google Drive（デスクトップ版の同期フォルダ）へ複製する。
# コピーのみ。コピー先のファイルを削除・上書き圧縮しない（履歴は消さない）。

set -u

SRC="$HOME/Desktop/investing_OS"

# ▼ ここだけ自分の環境に合わせて書き換える（Google Drive デスクトップ版のパス）
#   例: /Users/dcr3104/Library/CloudStorage/GoogleDrive-hacsat88@gmail.com/マイドライブ/investingOS-backups
DEST="/Users/dcr3104/Library/CloudStorage/GoogleDrive-hacsat88@gmail.com/マイドライブ/investing0S_backup"

LOG="$SRC/dev/scripts/backup-to-drive.log"
stamp() { date "+%Y-%m-%dT%H:%M:%S%z"; }

if [ ! -d "$SRC/backups" ]; then
  echo "$(stamp) FAILED 送り元が見つからない: $SRC/backups" >> "$LOG"; exit 1
fi

# Google Drive がマウントされていない時は何もしない（空フォルダを作って成功と誤認しないため）
DRIVE_ROOT="${DEST%/investingOS-backups}"
if [ ! -d "$DRIVE_ROOT" ]; then
  echo "$(stamp) SKIPPED Google Driveが未マウント: $DRIVE_ROOT" >> "$LOG"; exit 0
fi

mkdir -p "$DEST"

# ZIPは内容不変なので、コピー先に無いものだけ送る。--delete は使わない
rsync -a --ignore-existing "$SRC/backups/" "$DEST/" 2>>"$LOG"
RC=$?

# どの版が現在の正本かを併せて残す
if [ -f "$SRC/data/current.json" ]; then
  cp -p "$SRC/data/current.json" "$DEST/current.json.$(date +%Y%m%d)" 2>>"$LOG"
fi

COUNT_SRC=$(ls -1 "$SRC/backups"/*.zip 2>/dev/null | wc -l | tr -d ' ')
COUNT_DST=$(ls -1 "$DEST"/*.zip 2>/dev/null | wc -l | tr -d ' ')

if [ "$RC" -eq 0 ] && [ "$COUNT_DST" -ge "$COUNT_SRC" ]; then
  echo "$(stamp) SUCCESS 送り元${COUNT_SRC}件 / コピー先${COUNT_DST}件 → $DEST" >> "$LOG"
else
  echo "$(stamp) FAILED rsync=$RC 送り元${COUNT_SRC}件 / コピー先${COUNT_DST}件" >> "$LOG"; exit 1
fi

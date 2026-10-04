---
name: scr
description: 東証普通株の高回転スクリーニング（20営業日売買代金÷時価総額）を実行する。引数は growth / prime top=10 / mincap= maxcap= など。
---

# /scr [引数] — 高回転スクリーニング

先頭行に `scr/` と書いた場合と同じ。手順と構文の正本は `knowledge/25-screening.md`。不明な引数は推測せずエラーにする。

1. 25の母集団・除外条件に従って出典付きの入力JSONを集める（全銘柄を網羅できなければ PARTIAL と明記）。
2. `python3 app/screening.py scr/ <引数> --input <入力.json> --format markdown` で検査・順位化する。入力が無ければ DATA_REQUIRED。
3. 25の「出力順」で示す。順位は投資評価・推奨ではないと明記する。米国株には使わない。

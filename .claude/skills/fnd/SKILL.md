---
name: fnd
description: 法定開示の財務指標だけで東証の調査候補を抽出する財務スクリーニング。引数は growth / prime top=10 / profile=tenbagger|quality|cash など。
---

# /fnd [引数] — 財務スクリーニング

先頭行に `fnd/` と書いた場合と同じ。手順と構文の正本は `knowledge/26-fundamental-screening.md`。入出力例は `examples/`。

1. EDINET DB 等で指標ごとに出典IDを付けて入力JSONを作る。欠損は0で埋めず「判定不能」に分ける。
2. `python3 app/fundscreen.py "fnd/ <引数>" --input <入力.json> --format markdown`（コマンドは引用符で1つにまとめる） で計算・順位化する。
3. 26の「出力順」で示す。順位は条件の充足度であり、投資評価・買い順位ではないと明記する。米国株には使わない。

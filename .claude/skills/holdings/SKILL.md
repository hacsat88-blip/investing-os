---
name: holdings
description: 保有のテキストやスクリーンショットをinvestingOSの台帳に取り込むための提案JSONを作る。「保有を更新」「このスクショを取り込んで」で使う。
---

# /holdings — 保有の取込み（提案まで）

手順の正本は `knowledge/10-portfolio-operations.md`（米国株は同文書の米国規則、価格は28）。

1. `python3 app/store.py read` で最新版を読み、version を控える。
2. 入力からコード・名称・口座区分・数量・取得単価・価格・通貨・日時を抜き出す。読めない値は空欄。**スクショに写っていない銘柄を削除扱いにしない。**
3. 既存行と一意に照合する（英字入りコードも文字列のまま、同一銘柄の別口座は別行）。照合できない行は提案に入れず、確認事項に回す。
4. 変更を「新規／数量変更／削除候補／価格のみ／メモのみ」に分けて表で示す。売買があったとは推定しない。
5. `proposals/proposal-<YYYY-MM-DD>-holdings.json` に提案JSON（version・tables・reason。reasonに `ai:claude-code` など実行環境）を書き、`python3 app/store.py proposal --input <file>` で検査する。
6. ユーザーに「アプリで差分を確認して保存してください」と伝える。保存後に再度 read して反映を確認する。
7. 偏り・損失経路・良い点・改善案・特徴を伸ばす案を短く添える。Target・枠の変更は別の承認が必要。

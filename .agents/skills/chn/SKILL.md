---
name: chn
description: テーマ・ニュース・銘柄を起点に、市場が連想済みの銘柄（1次）の先にある不可欠な供給者（2次・3次）を一次資料で確かめ、星付きで並べる。先頭行が chn/ のとき、または /chn で呼ばれたときに使う。Claude Code と Google Antigravity の共通スキル。手順の正本は knowledge/29-chain-screening.md。
---

# chn 連鎖スクリーニング

1. `python3 app/store.py read` を実行し、実行環境（ローカル／チャット）と current.json の版を確定する。actor は Claude Code=`ai:claude-code`、Cowork=`ai:claude-cowork`、Antigravity=`ai:antigravity`。
2. `knowledge/29-chain-screening.md` を読み、その手順・星の定義・出力順に従う。本ファイルと食い違えば 29 に従う。
3. 財務・決算の扱いは `knowledge/20-security-analysis.md`、出典の優先順と到達性は `knowledge/40-data-sources.md` に従う。その回に使えない接続ツールは「未接続」と書き、利用済みと主張しない。
4. 保有・調査候補との重複は、読み込んだ版の holdings.csv と research.csv で確認する。
5. 調査候補を残す場合は、research.csv・sources.csv への提案JSON（version・tables・reason、reason に actor）を `proposals/` に作り、`python3 app/store.py proposal` で検査する。保存はユーザーが画面で行う。
6. `data/` を直接編集しない。星や並び順を買い順位として扱わない。発注株数を出さない。

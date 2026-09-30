---
name: research
description: 銘柄・ETF・投資信託を一次資料ベースで調査し、investingOSの形式（仮説・反対仮説・撤回条件・保有重複）で結論を出す。「〇〇を調べて」で使う。
---

# /research <銘柄・コード> — 銘柄調査

手順の正本は `knowledge/20-security-analysis.md`、出典の扱いは40、撤回条件の書式は27。

1. 対象を一意に特定する（市場・コード・名称）。
2. 一次資料：日本＝EDINET DB・適時開示・決算説明資料、米国＝SEC EDGAR。現在価格は時刻と出典付きで取る。
3. 確認：事業とKPI、CF、希薄化、バランスシート、評価、反対仮説、撤回条件（`@falsify` 形式を提案）、保有との重複（`app/store.py read` が使えれば holdings・exposures と照合）。
4. Fact／Estimate／Unknownを分け、各主要主張に出典を付ける。証拠不足なら「判断保留」と明記する。
5. 結論を1行目に書く。未保有なら research.csv の追記案、保有中なら theses.csv の更新案として提案JSONを作ってよい（保存はユーザー）。

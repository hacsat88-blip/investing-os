# 28 相場台帳 quotes.csv v1

保有台帳（holdings.csv）は数量・取得原価・口座・枠という変化の遅い事実を持つ。価格とFXは変化が速い。これを同じ行に置くと、価格を1つ直すたびに正本の行を触ることになり、どの価格がどの出典から来たのかも残らない。v4.4 から、相場は出典付きの別台帳に積む。

## 列
`id, holdingId, code, kind, value, currency, asOf, retrievedAt, quality, sourceId, note`

- `kind`：`PRICE`（株価・ETF価格）、`NAV`（投信の評価額・基準価額）、`FX`（通貨ペア）。
- `PRICE`/`NAV` は holdingId 必須で、保有台帳に存在するIDだけを受け付ける。
- `FX` は holdingId を空欄にし、`code` に `USDJPY` のようなペアを書く。
- `value` は正の数のみ。`asOf` と `sourceId` は必須。`asOf`/`retrievedAt` はISO形式のみ（例 `2026-09-18T15:30:00+09:00`）で、`2026-09-18 close` のような曖昧な表記は拒否する。場中/終値の区別は note に書く。
- 同じ対象・種別・基準日時の重複は拒否する。過去の相場行は消さず積む。

## 反映の手順
```
python3 app/quotes.py status                              # 鮮度とズレの点検
python3 app/quotes.py template --output quotes-input.json # 入力の雛形
python3 app/quotes.py ingest --input quotes-input.json --output proposal.json
```
`ingest` は相場行を積み、保有台帳への反映案（PROPOSED）を作る。保存はしない。ユーザーがアプリで差分を確認して保存する。

反映の規則：

- 円建て：`marketValueJpy = 数量 × 価格`。外貨建て：同じ入力に該当通貨ペアのFX行が無ければ反映しない。現在FXで取得原価を逆算しない。
- `pnlJpy` は取得原価がある時だけ再計算する。無ければ空欄のままにし、未確定として表示する。
- iDeCo（`kind=NAV`）は同時点の報告損益 `pnlJpy` が入力に無ければ反映しない。評価額だけ新しく損益が古い状態を作らないためである。
- 反映されなかった行も相場台帳には残る。証拠は捨てず、台帳だけを中途半端に更新しない。

## 鮮度判定
`status` は保有ごとに、相場の有無、経過日数、保有台帳の価格とのズレを分けて出す。`NO_QUOTE`（出典付き相場が無い）、`FRESH`（3日以内）、`AGING`（3日超）、`STALE`（7日超）、`MISMATCH`（保有台帳の価格と0.5%以上ズレ）。判定のみで、保有台帳は書き換えない。

`MISMATCH` は「どちらかが古い」という事実であって、どちらが正しいかは言わない。基準日時と出典を見て決める。

## Google Finance・Web からの取り込み（2026-10-20 改訂）
2026-10-20より TradingView MCP を廃止し、Google Finance・Yahoo!ファイナンス・トレーダーズ・ウェブ等のWeb経路を主経路とする（40-data-sources.md §2・§3）。

手順：
1. 日本株は `TYO:<コード>`（Google Finance）または Yahoo!ファイナンス／トレーダーズ・ウェブ、米国株は `NYSE:<ティッカー>` / `NASDAQ:<ティッカー>`（Google Finance / Yahoo Finance）、為替は `USD-JPY` 等で価格・レートと表示日時を確認する（価格は原則2経路で照合）。
2. 画面に表示された価格を `value`、基準日時をISO形式（オフセット必須）で `asOf` にする（東証大引け後の確定終値は当日 `15:30:00+09:00`、米国株の通常取引終値は現地取引日の `16:00:00-04:00` または `-05:00`）。表示時刻がない値は台帳へ入れない。
3. `retrievedAt` は実際に取得した日時。`sourceId` は取得元の出典行（2経路照合した場合はセミコロン区切りまたは主経路の出典に照合先をnote記録）。

`quality` の決め方：

- **場が引けたあとの確定終値 → `FACT`。**
- **ザラ場中に取った値・遅延表示の途中値 → `EST`。** 場中値をその日の終値として書かない。

取れないもの・手入力対象：PTS価格（取引市場・時刻・出来高・日中終値基準日が揃わない限り `UNKNOWN`）、投信の基準価額、iDeCoの資産残高。投信・iDeCoは従来どおり証券会社・運営管理機関の画面から手入力する。

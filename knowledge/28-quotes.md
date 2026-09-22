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

## TradingView MCP からの取り込み（2026-09-21 追加）
使うのは `get_ohlcv`（日足）。気配値ツールは429に当たりやすく、OHLCVは429の最中でも通った。

手順：
1. `get_ohlcv` を `symbol=TSE:<コード>` `interval=1D` `count=4` 程度で呼ぶ。`TSE:` は必須。
2. 最終バーの `c`（終値）を `value`、`t`（UNIX秒・UTC）を日付に変換して `asOf` にする。バーの `t` は当日 00:00 UTC ＝ JST 09:00 を指すので、**日付部分だけを使う**。
3. `retrievedAt` は実際に呼んだ日時。`sourceId` は TradingView MCP 用の出典行。

`quality` の決め方：

- **場が引けたあとの終値 → `FACT`。** 2026-09-21に3銘柄で証券口座表示と完全一致することを実測した。
- **ザラ場中に取った値 → `EST`。** APIが「15分以上遅延」「最終バーは確定値ではない」と明示している。
- リアルタイム配信は別料金（日本・米国で個別課金）であり、当システムは契約しない。**遅延前提で運用する。**

取れないもの：PTS価格（前後場外のバーが無い）、投信の基準価額、iDeCoの資産残高。これらは従来どおり証券会社・運営管理機関の画面から手入力する。

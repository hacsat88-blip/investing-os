# 31 監視ダッシュボード v1

2026-09-24制定。監視の結果を、文章のレポートに加えて1枚のHTMLダッシュボードで見られるようにする。**判断はAI、描画はスクリプト**に分ける。どのAIが監視を実行しても、同じ形式のJSONを書けば同じ画面になる。

## 流れ
1. 監視の各回（30）の終わりに、実行AIが `monitoring/runs/<YYYY-MM-DD>-<slot>.json` を書く（形式は下記 monitor-run-v1）。
2. 続けて `python3 app/monitor_view.py --ledger-version <current.jsonのversion>` を実行し、`monitoring/dashboard.html` を作り直す。
3. ユーザーはMacのブラウザで `monitoring/dashboard.html` を開く。

`monitoring/` はgit管理外であり、ダッシュボードもJSONもGitHubへ行かない（80 §2）。画面は外部のスクリプト・フォント・画像を読み込まない。スクリプトはネットワーク取得・CSV台帳の読み書き・通知を行わない。

## monitor-run-v1
| 項目 | 必須 | 内容 |
|---|---|---|
| schema | 必須 | `monitor-run-v1` |
| slot | 必須 | `0730` `0905` `1135` `1540` `2200` のいずれか |
| actor | 必須 | 実行AI（例 `ai:claude-code`） |
| startedAt | 必須 | オフセット付きISO日時 |
| status | 必須 | SUCCESS / PARTIAL / FAILED / SKIPPED（70と同じ） |
| detail | 任意 | 取得範囲・欠測・スキップ理由を短く |
| alerts[] | 任意 | code, name, stars（1〜5か null）, direction（POSITIVE/NEGATIVE/MIXED/NEUTRAL/UNKNOWN）, confidence, what, publishedAt（オフセット付きか null）, sourceId, url, checkNext |
| holdings[] | 任意 | holdingId, code, name, currency, price, prevClose, freshness（FRESH/AGING/STALE/NO_QUOTE）, thesisStatus（SUPPORTED/WATCH/CHALLENGED/UNREVIEWED か null） |
| price / prevClose | 任意 | {value（正の数）, asOf（オフセット付き）, quality（FACT/EST/UNKNOWN）}。取れなければ項目ごと null |
| errors[] | 任意 | route, message（取得できなかった経路） |

書き方の規則：
- 取れなかった値は null。**0や空文字で埋めない**。星を付けられない材料は stars=null（30の「取得不能に星1を付けない」）。
- 米国株の asOf は現地時刻とオフセットのまま書く（40 §3）。日本時間へ読み替えない。
- 評価額・数量・取得単価・損益・口座情報は書かない。ダッシュボードにも出さない（保有画面で確認する）。
- JSONは監視の記録であり正本ではない。news/sources への取込は従来どおり提案→ユーザー承認（30）。

## 画面の規則（スクリプトが保証する）
- 各監視枠の直近の実行を、07:30〜22:00の並びで表示する。実行記録が無い枠は「実行記録なし」。
- 材料は直近48時間の SUCCESS/PARTIAL の回から、星の降順・同じ星は新しい順に並べる。FAILED/SKIPPED の回の材料は出さない。同じ sourceId（無ければ url）は1件にまとめる。
- 前回比は price と prevClose が両方ある時だけ計算する。無ければ「算出不可」。
- 保有ごとに価格の基準日が異なる時は、その旨を表示する。
- 形式に合わないJSONは画面の「読み込めなかったレポート」に理由付きで出し、終了コード1を返す。黙って捨てない。
- 文字列はすべてエスケープし、リンクは http/https のみ有効にする。

## 受入
`python3 dev/tests/test_monitor_view.py`：正常描画、欠損を0にしない、前回比の計算、壊れたJSONの列挙、形式違反の拒否、0以下の価格の拒否、米国時刻のオフセット保持、基準日の混在表示、星未評価の表示、エスケープと危険なリンクの無効化、FAILED回の材料除外、星の並び順、外部読込なし・金額列なし、未登録枠の表示。

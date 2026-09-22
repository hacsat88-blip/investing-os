# v4.4 検証記録 — 2026-09-20

## 追加
- `app/fundscreen.py`（`fnd/` 財務スクリーニング実行器）、`app/falsify.py`（反証エンジン）、`app/quotes.py`（相場台帳ユーティリティ）。
- `quotes` 台帳をスキーマへ追加（全13台帳）。`insights.quote_status` を `/api/state` に追加。
- knowledge 26 / 27 / 28。tests/test_upgrades.py（26件）。

## 合格した検証（Mac上で実行）
- 新規26テスト合格、既存16テスト（tests/test_screening.py）合格。JavaScript構文検査合格。
- `fnd/` 構文：既定3市場TOP5、市場指定、top範囲外、不明引数、重複指定、mincap>maxcap、未知profileを拒否。先頭行だけを解釈し、2行目の `fnd/` は無視。
- `fnd/` フェイルクローズ：必須指標の欠落と出典IDの欠落はどちらも「判定不能」へ落ち、0で埋めない。非普通株・ゲート不通過・時価総額帯は除外理由付きで分離。カバレッジ不明はPARTIAL＝「取得済み範囲内順位」。出力に PROPOSED / APPROVED / EXECUTED / CSV_SYNCED を生成しない。
- 反証エンジン：条件成立→CHALLENGED、観測なし→WATCH（支持にしない）、出典なし観測は無視、EST のみの不成立→WATCH、自由文のみ→UNTESTABLE、`@stale` の経過日数判定。
- 相場台帳：値0・負値・出典なし・非ISO日時・不正種別・不正品質・未知保有ID・非対応通貨・重複を拒否。FXに保有IDを付けた行を拒否。
- 相場反映：円建ては数量×価格で再計算、外貨建てはFX行が無ければ反映せず相場行だけ残す、iDeCoは同時点の報告損益が無ければ反映しない。古いversionの提案は CONFLICT で拒否。
- 保存：新スキーマは schemaVersion 4.4 で保存、再読で一致。旧4.2/4.3の版は quotes を空として読める（後方互換）。判断履歴の削除・改変は拒否。
- HTTP：`/api/state` に quotes を追加後も起動・応答。外部Originからの POST は403。

## 未検証・対象外
- 実勢価格・基準価額の取得そのもの（相場台帳は出典付き入力を受ける器であり、取得経路ではない）。
- `scr/` の東証全銘柄カバレッジ。現在の実行環境では日次売買代金の一括取得経路が無く、DATA_REQUIRED/PARTIALのまま。
- 保有10件の仮説カード・構成内訳・撤回条件の中身は未入力。`falsify.py audit` は10件すべて EMPTY＝検証不能と報告する。
- ChatGPT Projectへの再アップロード、通知到達、別媒体バックアップ。

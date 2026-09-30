---
name: monitor
description: investingOSの保有監視を1回分実行する（07:30/09:05/11:35/15:40/22:00の各枠）。定期タスクや「監視して」「09:05の監視」で使う。引数は枠（例 0905）。
---

# /monitor <slot> — 保有監視 1回分

手順の正本は `knowledge/30-monitoring-alerts.md`・`31-monitoring-dashboard.md`・`70-health-and-agents.md`。食い違えばknowledgeに従う。
slot は `0730` `0905` `1135` `1540` `2200` のいずれか。不明・範囲外なら実行せず理由を返す。

## 1. 実行者の確認（最初に必ず）
```
python3 app/runner_guard.py check --slot <slot> --actor ai:claude-code --record
```
- 終了コード 0：続行。
- 3（runner不一致）/ 4（未登録）：SKIPPEDとして記録済み。取得・通知・カーソル更新をせずに終了し、理由を1行で報告する。
- 2：state.jsonの異常。何も書き換えずに障害として報告する。
- Coworkから手動で実行する場合は actor を `ai:claude-cowork` にする（登録が違えばSKIPPEDになるのが正しい動き）。

## 2. 実行条件
- 日本の枠：JPXカレンダーで取引日を確認する。休場ならSKIPPED。
- 0730：holdingsに currency=USD の保有が1件以上あり、かつ直前の米国取引日がある時だけ（日本時間の火〜土）。どちらかが無ければSKIPPED。
- 判定できなければ営業日と断定せず、障害として記録する。

## 3. 台帳を読む
`python3 app/store.py read` で最新版（version）とholdingsを読む。固定の銘柄リストを使わない。

## 4. 情報を集める
経路の優先順位は `knowledge/40-data-sources.md` §2。日本＝適時開示・企業IR・EDINET DB、米国＝SEC EDGAR（8-K・10-Q・10-K）と発行体IR、価格＝TradingView MCP。使えなかった経路は errors[] に書き、取得済みと書かない。
重要度は星1〜5・方向・確度・公表時刻（原本のTZ＋日本時間）・出典を付ける。取得不能や新情報なしに星1を付けない。

## 5. 記録する（この順）
1. レポート：`monitoring/<YYYY-MM-DD>_<HHMM>_<枠名>.md`（枠名：0730=米国引け後、0905=寄り付き後、1135=前場、1540=大引け後、2200=PTS夜間）
2. 実行JSON：`monitoring/runs/<YYYY-MM-DD>-<slot>.json`（monitor-run-v1、31の表どおり）
3. ダッシュボード：`python3 app/monitor_view.py --ledger-version <version>`
4. `monitoring/state.json`：lastAttemptAt・lastStatus・reportPath・detail・cursorsを更新。**lastSuccessAt は SUCCESS の回だけ**。失敗した経路のカーソルは進めない。
5. news/sourcesへの取込候補があれば `proposals/` に提案JSONを作り `python3 app/store.py proposal --input <file>` で検査する。**holdingsは書き換えない。**

## 6. 報告
重要な新情報・重要度変更・期限接近・障害/復旧がある時だけ通知する。変化なしなら通知しない。最後に「状態・件数・レポートのパス」を3行以内で返す。

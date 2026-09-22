# 40 出典・鮮度・利用可能な経路 v4.4

更新：2026-09-22（v4.3 → v4.4）。変更の趣旨は特定サイトへの乗り換えではなく、用途別の**出典階層化**、**到達性の実測記録**、**他文書との整合条項**の追加。過去版の記述は §7 に環境記録として保持する。

## 1. 原則（v4.3から継承・変更なし）

出典種別：USER_PRIMARY（ユーザーの保有/約定資料）、REGULATOR_PRIMARY（原本法定開示）、ISSUER_PRIMARY（発行体IR）、MARKET_DATA（価格/FX/PTS）、SECONDARY（報道）、ESTIMATE（推定）。
確度：CORROBORATED/SINGLE_SOURCE/CONFLICTED/UNVERIFIED。公表日時、取得日時、データ基準日時を別に持つ。原本を取得していないMCP集約値を無条件に一次確認済みとしない。
優先：企業/運用会社原本とEDINET/JPX → 検証可能な市場データ → 二次報道。
**到達性は実行回ごとに確認する。過去の403/500/robots制約は当時の環境記録であり、永久的な禁止や現在の到達性の証明ではない。アクセス制限の回避はしない。**
EDINET DBのget_financialsは有価証券報告書中心。最新決算はget_earningsや発行体IRも使い、データ期間・docID・原本URLを確認。AI分析スコアは評価モデルであり開示事実ではない。
為替は値の更新時刻を確認し、日次APIの値をリアルタイムと表示しない。数値の出典が違う場合は価格・FXの時点差を明示する。

## 2. 個別銘柄調査の出典階層（新設）

| 用途 | 第1優先 | 第2（フォールバック） | 扱い |
|---|---|---|---|
| 価格・OHLCV・テクニカル指標 | TradingView MCP | Yahoo!ファイナンス、トレーダーズ・ウェブ | MARKET_DATA。フォールバックは**照合補助**であり正本にしない |
| 適時開示・材料（30暦日） | 発行体IRサイト（ISSUER_PRIMARY） | TDnet（自動取得不可の回は人がブラウザで確認） | 未確認期間を「材料なし」としない |
| 財務・法定開示 | EDINET MCP（REGULATOR_PRIMARY） | 発行体の決算短信・説明資料 | 期間・連結/単独・実績/予想を個別に持つ |
| 市場区分・母集団・取引日 | JPX | — | `scr/` `fnd/` の母集団定義は §5 のまま |
| 二次報道・ランキング・板情報 | 株探、みんかぶ、各証券 | — | SECONDARY。掲示板や板の強気比率は**需給指標ではない** |

運用ルール：

- **価格は2経路で照合する。この照合はMARKET_DATA（価格・FX・PTS）に限る。** 発行体IRとその発行体の法定開示は独立2ソースではなくCORROBORATEDにならない（20-security-analysis.mdの原則を維持）。
- **指標は正本を代替しない**：RSI/MACD/MA/ATR等はMARKET_DATAの派生値であり、材料・財務の未確認を補わない。撤回条件（27）の観測値に使う場合は **quality=EST** とし、算出元OHLCVのsourceIdと算出式を必ず残す。
- **受注・提携IRは「事実」と「収益寄与」を分離**：金額・粗利・計上期が未開示なら Fact=開示の事実／Unknown=業績インパクト と明記し、株価反応から金額を逆算しない。
- **バリュエーションの床の有無を明記**：赤字・高PBR銘柄では、フィボナッチ等の値動き由来の下値目標を「支持帯」と呼ばない。
- **フォールバック経路は1銘柄ずつの照合用**であり、東証全銘柄の一括取得には使えない。`scr/` のDATA_REQUIRED/PARTIAL原則（26-fundamental-screening.md）は変更しない。
- **新しい経路を使った回は sources.csv に sourceId を登録**する（URL、公表時点、取得時点、データ基準時点、種別、確度）。50-qc-acceptance.mdの「出典参照切れ拒否」に合わせ、台帳の値だけを先に入れない。

## 3. 経路ごとの asOf / quality の書き方（新設・28と接続）

quotes.csvの`asOf`はISO形式のみ（例 `2026-09-18T15:30:00+09:00`）。経路別の規則：

- TradingView MCP 日足：バーはUTC秒で返るが、東証日足の終値は当日 `15:30:00+09:00` として書く。時間足・場中値は取得時刻をnoteに残す。**15分以上の遅延があり最終バーは確定値ではない**ため、場中値をその日の終値として書かない。
- Yahoo!ファイナンス／トレーダーズ・ウェブ：画面表示の日時をそのまま`asOf`にする。表示時刻がない値は`asOf`不明として台帳へ入れない。
- **PTS**：取引市場・価格時刻・出来高・比較する日中終値の基準日が揃わない限り quality=UNKNOWN とし、quotes/newsへ入れない（30-monitoring-alerts.mdのPTS規則に従う）。22時時点は夜間途中であり最終値ではない。
- MCPが429等で失敗しOHLCVから自前計算した指標：MARKET_DATA派生のESTであり、quotes.csvの`PRICE`/`NAV`行にしない。

## 4. 到達性の実測記録（2026-09-22、Cowork/クラウド実行、TSE:485Aで検証）

本節は**その実行環境での実測**であり、26-fundamental-screening.mdが記録するCodex環境の前提（外部一括取得不可）を否定しない。Web取得は1URLずつで、母集団の一括取得は依然できない。

- TradingView MCP：OHLCV（1D/1h）取得成功。`get-technicals-rating`と`get-symbol-data`は**HTTP 429（レート制限）で連続失敗**。対処順は ①時間を空けて再試行 ②OHLCVから自前計算（EST扱い） ③フォールバック経路。
- Yahoo!ファイナンス（finance.yahoo.co.jp/quote/<code>.T）：取得成功。株価・出来高・時価総額・PER/PBR・夜間PTS・関連ニュース要旨。**利用規約上の自動取得はグレーのため正本化せず照合補助に限定**。
- トレーダーズ・ウェブ（traders.co.jp/stocks/63_<code>/）：取得成功。株価・時価総額・**次回決算予定日**。ニュース本文は薄い。
- 発行体IR（例 power-x.jp/news/）：取得成功。日付付きリリース一覧が取れ、**材料確認の実質的な一次経路**。
- TDnet（release.tdnet.info）：**robots.txtにより自動取得不可**。回避はしない。必要時は人がブラウザで確認する。
- kabutan.jp、minkabu.jp：**HTTP 403**（ページ直取得不可）。検索結果のリンクとしては有用。次回も到達性は再確認する。
- EDINET MCP：`search_companies`／`get_earnings`／`get_financials`の呼出成功（E40934で確認）。財務の裏取りが必要な回は必ず併用する。

## 5. `scr/` のデータ経路（v4.3から実質変更なし）

母集団はJPXの上場銘柄情報等で市場区分と商品種別を確認し、プライム・スタンダード・グロースの普通株だけを対象にする。ETF、ETN、REIT、インフラファンド、優先株等は除外する。月末一覧を使う場合は、基準日までの新規上場、上場廃止、市場変更との時点差を示す。

順位計算には同じ基準日の時価総額と、銘柄別の直近20営業日の売買代金が必要。主指標と1日・5日・20日の補助指標はすべて「各期間の売買代金合計÷基準日時価総額」で計算する。市場データ提供者の「出来高回転率」を混ぜる場合は式を別表示し、同じ指標名で混在させない。取得日数不足、休場日混入、時価総額日の不一致、単位不明、全銘柄カバレッジ不明はUNKNOWN/PARTIALとする。

財務OverlayはEDINET/法定開示と発行体の最新決算を優先し、売上、営業利益、営業CF、ROE、自己資本比率の期間・連結/単独・実績/予想を個別に持つ。材料は基準日を含む直近30暦日を**§2の優先順（発行体IR→TDnet→二次ニュース）**で確認する。TDnetの公開閲覧期間・検索経路・robots制約を理由に、未確認期間を「材料なし」としない。信用需給と希薄化は確認できる別資料を使い、株価上昇だけから混雑を断定しない。

ローカルの `app/screening.py` はネットワーク取得を行わない。利用中のWeb/MCP/金融スキル、または出典付きエクスポートで作った `scr-input-v1` を渡す。未接続時は `DATA_REQUIRED` を返し、入力のないランキングを生成しない。

## 6. 他文書との整合条項（新設）

- **経路の優先順位は本書§2を正本とする。** 20-security-analysis.md（v4.4）と25-screening.md（v1.1）の該当文も同じ順に揃えた。30-monitoring-alerts.mdの「企業IR/適時開示/EDINET DBを材料の根拠とし、株探等は価格・PTSまたは二次報道として区別」と本書§2は同じ内容である。
- 本書はデータの**取得経路**のみを定める。判断状態（PROPOSED/APPROVED/EXECUTED）、承認、保存の手順は00-governance.md、10-portfolio-operations.md、50-qc-acceptance.mdに従う。経路を追加しても方針変更承認の要否は変わらない。
- 「株深」はユーザー表記のゆれとして「株探」を指すものとして扱う（30-monitoring-alerts.mdと同じ扱い）。

## 7. 参照公式ページと過去の環境記録

- JPX東証上場銘柄一覧 https://www.jpx.co.jp/markets/statistics-equities/misc/01.html
- JPX TDnet概要 https://www.jpx.co.jp/equities/listing/disclosure/tdnet/
- JPX現物取引時間 https://www.jpx.co.jp/equities/trading/domestic/01.html （9:00〜11:30、12:30〜15:30）
- JPXカレンダー https://www.jpx.co.jp/corporate/about-jpx/calendar/
- Japannext PTS https://www.japannext.co.jp/ja/pts （夜間17:00〜翌6:00。証券会社の受付時間とは別）
- ローカル定期タスクの実行条件 https://learn.chatgpt.com/docs/automations?surface=app

2026-09-13の環境確認記録（v4.3より保持）：このCodex環境にEDINET DBツールの定義は存在する。実銘柄財務の呼出成功、株価/PTS全銘柄取得、旧Artifact DBとの接続は未検証。旧Artifact URLは当時のWeb読取で取得できなかった。

## 8. 秘密情報

口座番号、認証情報、住所はCSVに含めない。外部AIへ渡すのはユーザーが必要とする保有/分析情報のみ。アプリ自体は外部ネットワークへ送信しない。

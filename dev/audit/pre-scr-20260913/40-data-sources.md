# 40 出典・鮮度・利用可能な経路 v4.3

出典種別：USER_PRIMARY（ユーザーの保有/約定資料）、REGULATOR_PRIMARY（原本法定開示）、ISSUER_PRIMARY（発行体IR）、MARKET_DATA（価格/FX/PTS）、SECONDARY（報道）、ESTIMATE（推定）。
確度：CORROBORATED/SINGLE_SOURCE/CONFLICTED/UNVERIFIED。公表日時、取得日時、データ基準日時を別に持つ。原本を取得していないMCP集約値を無条件に一次確認済みとしない。

優先：企業/運用会社原本とEDINET/JPX → 検証可能な市場データ → 二次報道。株探・松井証券・stockanalysis等の到達性や表示時点は実行回に確認する。旧文書の403/500等は当時の環境記録であり永久的禁止や現在の利用可能性の証明ではない。アクセス制限の回避はしない。
EDINET DBのget_financialsは有価証券報告書中心。最新決算はget_earningsや発行体IRも使い、データ期間・docID・原本URLを確認。AI分析スコアは評価モデルであり開示事実ではない。
為替は値の更新時刻を確認し、日次APIの値をリアルタイムと表示しない。数値の出典が違う場合は価格・FXの時点差を明示する。

2026-09-13の今回確認：このCodex環境にEDINET DBツールの定義は存在する。実銘柄財務の呼出成功、株価/PTS全銘柄取得、旧Artifact DBとの接続は未検証。旧Artifact URLは今回のWeb読取で取得できなかった。

参照公式ページ（2026-09-13確認）：
- JPX現物取引時間 https://www.jpx.co.jp/equities/trading/domestic/01.html （9:00〜11:30、12:30〜15:30）
- JPXカレンダー https://www.jpx.co.jp/corporate/about-jpx/calendar/
- Japannext PTS https://www.japannext.co.jp/ja/pts （夜間17:00〜翌6:00。証券会社の受付時間とは別）
- ローカル定期タスクの実行条件 https://learn.chatgpt.com/docs/automations?surface=app

口座番号、認証情報、住所はCSVに含めない。外部AIへ渡すのはユーザーが必要とする保有/分析情報のみ。アプリ自体は外部ネットワークへ送信しない。

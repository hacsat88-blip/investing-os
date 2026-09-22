# scr/ 実装・受入結果

実施日：2026-09-13

## 対象
- 会話制御構文：`scr/`、市場指定、top、mincap/maxcap。
- 決定的実行器：`app/screening.py`。
- 仕様：`knowledge/25-screening.md`。
- 既存統治・銘柄分析・データソース・QC・調査優先順位との接続。

## 結果
- 新規screeningテスト16件：PASS。
- 既存storeテスト7件：PASS。
- 既存v4.3 insights/healthテスト8件：PASS。
- `app/screening.py` 構文コンパイル：PASS。
- `app/store.py read`：PASS。

合計31テストPASS。既存CSV正本のcurrent.json、revisions、backupsは変更していない。

## 確認した境界
- 20営業日累計売買代金÷基準日時価総額を主順位に使用。
- 1/5/20日の補助指標を同一定義で計算。
- Prime/Standard/Growthを分離し、普通株以外を除外。
- topと時価総額（億円）の境界を検査。
- 20営業日不足、同日重複、時価総額欠損/0/基準日不一致を拒否または除外。
- 母集団・取引日・出典が未確認ならPARTIAL/UNKNOWN。
- 財務、4リスク、30日材料、4分類の欠損を0で補完しない。
- ランキングは投資評価へ写像せず、NOT_EVALUATEDのまま。
- 入力なしではDATA_REQUIRED。ネットワーク取得やCSV台帳更新を行わない。

## 未接続
東証全銘柄の日次売買代金・時価総額を一括取得する市場データ経路は今回接続していない。実データでの各市場TOP5、財務Overlay、30日材料の実行結果は未生成。ChatGPT Projectの同期済みsourcesは参照専用のため今回更新していない。

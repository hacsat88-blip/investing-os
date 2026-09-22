# 60 投資仮説・調査課題・重複・提案比較 v4.3

## ① 投資仮説カード
保有IDごとに1枚。reason/expectation/metric/baseline/latest/threshold/change/counterCase/falsifier/reviewOn/reviewedAt/thesisStatus/sourceIdを保存する。
UNREVIEWED（未確認）/SUPPORTED（支持）/WATCH（注視）/CHALLENGED（反証材料）を使う。仮説状態と売買状態は別。未確認の指標や保有理由は空欄。コードだけでなく保有IDで口座の違いを保つ。
ニュース・決算を読んだら、どの仮説と指標に関係するかを示す。最新値と前回値の単位・期間を揃え、変化、理由、一次資料を記録する。材料だけで機械的に仮説を破壊済みとしない。

## ② 調査優先順位
question、decisionLink、impact、uncertainty、urgency、effort、dueOn、researchStatus、nextAction、result、sourceId。数値は各1〜5または空欄。
期限超過→影響×不確実性＋緊急度×2の降順→同点は負担の小さい順。完了は待ち行列から外す。未採点を0点とみなさず別表示。点数の理由はnoteへ記載し、精密な予測としない。
次の調査には「決算説明資料の利益率内訳を確認」のように対象と判定目的を書く。確認できたらresultと出典を残し、解決した課題だけDONEにする。

`scr/` の上位入りはresearch.csvへの自動追加条件ではない。ユーザーが継続調査を選んだ候補だけ、順位基準日・スクリーニング式・最初の反証事項を明記した更新案にする。回転率順位をimpact、uncertainty、urgencyの採点や投資成功確率へ写像しない。

## ③ 重複とストレス
exposuresはholdingId、dimension（ISSUER/SECTOR/CURRENCY）、component、weight（0〜1の小数）、asOf、quality、sourceId。
同一保有・分類・構成要素は重複不可。同一保有・分類の合計は1以下。未知・未登録分は未割当として残す。集計は親商品の登録評価額×取得済み構成比。各分類内で集計し、銘柄・業種・通貨を互いに足さない。部分構成データを100%へ再正規化しない。
タグ集計はタグが付いた商品の評価額合計であり、ETFの組入比率・相関・実質デルタではない。確認済み構成情報のない商品を名称だけで自動分類しない。価格評価日と構成日が異なる場合は両方を示す。
ストレス式：評価額×(1＋商品価格変化率)×(1＋FX変化率)。FX項はUSD建て行のみ。率はパーセント入力。商品価格変化率は商品そのものへの仮定なので、レバレッジ倍率を再度掛けない。円建て海外投信の内包FX、相関変化、日次レバレッジの経路は未モデル化。予測・最大損失・推奨として出さない。欠損時は部分小計と未算定件数を表示。

## ④ 提案比較
plansにはtitle、mode（HOLD/ADD/REBALANCE）、baselineHash、additionalCashJpy、feesJpy、taxJpy、benefit、risk、assumptions、invalidation、status、sourceId。
plan_itemsにはplanId、holdingId（未保有候補は空欄）、code/name/bucket、targetValueJpy、sourceId。保有IDがあるとき銘柄・枠は保有台帳から取得。未記載の保有は現状維持。新候補はコード・名称を必要とするが、その同一性・商品性は別途確認する。
比較対象は登録資産＋追加資金。未収録の既存現金は含めない。調整後資産＝登録小計＋追加資金−費用−税。未配分資金＝調整後資産−提案評価額合計。マイナスなら資金不足。最大商品比率と上位3商品比率は未配分資金も含む分母で算定。
追加資金案は保有縮小を含めない。現状維持は追加資金0・変更明細なし。税と費用の空欄を0にしない。金額配分の試算であり、売買単位・実行可能株数や商品内の実質重複を完全に評価するものではない。
baselineHashは比較元holdings.csvのハッシュ。元データ変更後は案を再検討し、単にハッシュを書き換えて古い判断を新しく見せない。保護枠の変更を含む案は別の方針変更承認が必要。画面の保存・比較は保有やTargetを変更しない。

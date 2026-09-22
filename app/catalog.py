#!/usr/bin/env python3
"""選択肢カタログ。保有理由と撤回条件を「選んで埋める」ための定義。

入力欄が空白のままになる最大の理由は、白紙から言語化させられることである。
ここでは分類と条件テンプレを用意し、選択＋数値で機械可読な撤回条件を生成する。
選択肢は思考の省略ではなく出発点なので、どの項目にも自由記述を併設する。
"""

REASONS = [
    {'code': 'GROWTH_TOPLINE', 'label': '売上が伸び続ける（市場拡大・シェア拡大）',
     'suggestMetrics': ['売上成長率'], 'suggestFalsifiers': ['REVENUE_GROWTH', 'PLAN_CUT']},
    {'code': 'MARGIN_EXPANSION', 'label': '利益率が上がる（価格決定力・構成改善）',
     'suggestMetrics': ['営業利益率'], 'suggestFalsifiers': ['OP_MARGIN', 'PLAN_CUT']},
    {'code': 'NEW_PRODUCT', 'label': '新製品・新サービスが立ち上がる',
     'suggestMetrics': ['売上成長率', '受注残前年比'], 'suggestFalsifiers': ['BACKLOG', 'PLAN_CUT']},
    {'code': 'STRUCTURAL_DEMAND', 'label': '構造的な需要（AI・電力・防衛などの長期テーマ）',
     'suggestMetrics': ['受注残前年比', '売上成長率'], 'suggestFalsifiers': ['BACKLOG', 'THEME_STALL']},
    {'code': 'TURNAROUND', 'label': '不振からの回復（黒字化・構造改革）',
     'suggestMetrics': ['営業利益率', '営業CF'], 'suggestFalsifiers': ['OP_CF', 'PLAN_CUT']},
    {'code': 'RERATING', 'label': '割安の見直し（評価水準の訂正）',
     'suggestMetrics': ['ROE'], 'suggestFalsifiers': ['ROE_DROP', 'PLAN_CUT']},
    {'code': 'CASH_RETURN', 'label': '株主還元（配当・自社株買い）',
     'suggestMetrics': ['営業CF'], 'suggestFalsifiers': ['OP_CF', 'DILUTION']},
    {'code': 'DEFENSIVE', 'label': '守備・分散（値動きの異なる資産を持つ）',
     'suggestMetrics': ['自己資本比率'], 'suggestFalsifiers': ['EQUITY_RATIO', 'DRAWDOWN']},
    {'code': 'INDEX_CORE', 'label': '指数・年金コア（長期積立、個別判断はしない）',
     'suggestMetrics': ['基準価額'], 'suggestFalsifiers': ['POLICY_CHANGE']},
    {'code': 'OPTIONALITY', 'label': '一発材料のオプション性（承認・大型受注など）',
     'suggestMetrics': ['営業CF'], 'suggestFalsifiers': ['BINARY_MISS', 'DILUTION', 'DRAWDOWN']},
    {'code': 'INHERITED', 'label': '過去に買ったまま。理由を言語化できていない',
     'suggestMetrics': [], 'suggestFalsifiers': ['DRAWDOWN', 'REVIEW_STALE']},
]

EXPECTATIONS = [
    {'code': 'EARNINGS_BEAT', 'label': '業績が計画を上回って伸びる'},
    {'code': 'MARGIN_UP', 'label': '利益率が段階的に上がる'},
    {'code': 'ORDER_GROWTH', 'label': '受注・契約が積み上がる'},
    {'code': 'MULTIPLE_UP', 'label': '評価水準（倍率）が切り上がる'},
    {'code': 'RECOVERY', 'label': '赤字・不振から黒字定着へ戻る'},
    {'code': 'STEADY_COMPOUND', 'label': '大きく動かず、長期で積み上がる'},
    {'code': 'EVENT_HIT', 'label': '特定の材料が実現する（時期は読めない）'},
]

METRICS = [
    {'code': '売上成長率', 'unit': '%', 'note': '前年同期比。連結/単独と実績/予想を分ける'},
    {'code': '営業利益率', 'unit': '%', 'note': '営業利益÷売上。IFRS等で開示形式が違う点に注意'},
    {'code': '営業CF', 'unit': '百万円', 'note': '営業キャッシュフロー。黒字/赤字の判定に使う'},
    {'code': '自己資本比率', 'unit': '%', 'note': '財務の耐久力'},
    {'code': '希薄化1年', 'unit': '%', 'note': '発行済株式数の1年変化。増資・新株予約権を含む'},
    {'code': '受注残前年比', 'unit': '%', 'note': '受注残高または受注高の前年比'},
    {'code': 'ROE', 'unit': '%', 'note': '自己資本利益率'},
    {'code': '取得単価からの騰落率', 'unit': '%', 'note': '自分の取得単価に対する現在値。事実であり予想ではない'},
    {'code': '基準価額', 'unit': '円', 'note': '投信・ETFの基準価額または価格'},
    {'code': '通期計画下方修正', 'unit': '回', 'note': '発生を1、未発生を0で記録する'},
    {'code': '主要顧客喪失', 'unit': '件', 'note': '発生を1、未発生を0で記録する'},
    {'code': 'ガバナンス事象', 'unit': '件', 'note': '不祥事・経営陣の突然の交代など。発生を1'},
]

FALSIFIERS = [
    {'code': 'REVENUE_GROWTH', 'kind': 'falsify', 'metric': '売上成長率', 'op': 'lt',
     'unit': '%', 'default': 0, 'valueLabel': '下回ったら撤回する成長率（%）',
     'label': '売上成長率が基準を下回る'},
    {'code': 'OP_MARGIN', 'kind': 'falsify', 'metric': '営業利益率', 'op': 'lt',
     'unit': '%', 'default': 10, 'valueLabel': '下回ったら撤回する利益率（%）',
     'label': '営業利益率が基準を下回る'},
    {'code': 'OP_CF', 'kind': 'falsify', 'metric': '営業CF', 'op': 'lte',
     'unit': '百万円', 'default': 0, 'valueLabel': '下回ったら撤回する営業CF（百万円）',
     'label': '営業CFが赤字になる'},
    {'code': 'EQUITY_RATIO', 'kind': 'falsify', 'metric': '自己資本比率', 'op': 'lt',
     'unit': '%', 'default': 40, 'valueLabel': '下回ったら撤回する自己資本比率（%）',
     'label': '財務の耐久力が落ちる'},
    {'code': 'DILUTION', 'kind': 'falsify', 'metric': '希薄化1年', 'op': 'gt',
     'unit': '%', 'default': 10, 'valueLabel': '超えたら撤回する1年の株式増加（%）',
     'label': '希薄化が想定を超える'},
    {'code': 'BACKLOG', 'kind': 'falsify', 'metric': '受注残前年比', 'op': 'lt',
     'unit': '%', 'default': -10, 'valueLabel': '下回ったら撤回する受注残前年比（%・マイナス可）',
     'label': '受注残が減り始める'},
    {'code': 'ROE_DROP', 'kind': 'falsify', 'metric': 'ROE', 'op': 'lt',
     'unit': '%', 'default': 8, 'valueLabel': '下回ったら撤回するROE（%）',
     'label': '資本効率が落ちる'},
    {'code': 'DRAWDOWN', 'kind': 'falsify', 'metric': '取得単価からの騰落率', 'op': 'lte',
     'unit': '%', 'default': -25, 'valueLabel': '撤回を考える下落率（%・マイナスで入力）',
     'label': '取得単価から大きく下落する'},
    {'code': 'PLAN_CUT', 'kind': 'falsify', 'metric': '通期計画下方修正', 'op': 'gte',
     'unit': '回', 'default': 1, 'valueLabel': '撤回する下方修正の回数',
     'label': '会社計画が下方修正される'},
    {'code': 'BINARY_MISS', 'kind': 'falsify', 'metric': '主要顧客喪失', 'op': 'gte',
     'unit': '件', 'default': 1, 'valueLabel': '撤回する件数',
     'label': '前提だった顧客・契約・承認が外れる'},
    {'code': 'GOVERNANCE', 'kind': 'falsify', 'metric': 'ガバナンス事象', 'op': 'gte',
     'unit': '件', 'default': 1, 'valueLabel': '撤回する件数',
     'label': '不祥事・経営陣の突然の交代'},
    {'code': 'THEME_STALL', 'kind': 'falsify', 'metric': '売上成長率', 'op': 'lt',
     'unit': '%', 'default': 10, 'valueLabel': 'テーマが業績に出ていないとみなす成長率（%）',
     'label': 'テーマが業績に結びつかない'},
    {'code': 'REVIEW_STALE', 'kind': 'stale', 'metric': '営業CF',
     'unit': '日', 'default': 120, 'valueLabel': '確認が途切れたとみなす日数',
     'label': '開示を追えていない'},
    {'code': 'POLICY_CHANGE', 'kind': 'stale', 'metric': '基準価額',
     'unit': '日', 'default': 90, 'valueLabel': '評価額の確認が途切れたとみなす日数',
     'label': '年金コアの確認が途切れる'},
]

BY_CODE = {f['code']: f for f in FALSIFIERS}


def rule_line(code, value=None):
    """テンプレ＋数値から、反証エンジンが読める1行を作る。"""
    tpl = BY_CODE.get(code)
    if tpl is None:
        raise ValueError('未知の撤回条件テンプレです: ' + str(code))
    number = tpl['default'] if value in (None, '') else value
    try:
        number = float(number)
    except (TypeError, ValueError):
        raise ValueError('撤回条件の基準値は数値です')
    text = ('%g' % number)
    if tpl['kind'] == 'stale':
        return '@stale %s %dd : %s' % (tpl['metric'], int(number), tpl['label'])
    return '@falsify %s %s %s %s : %s' % (tpl['metric'], tpl['op'], text, tpl['unit'], tpl['label'])


def tagged(code, options, free_text=''):
    """選択肢コードと自由記述を1つの欄にまとめる（1行目が選択、以降が自由記述）。"""
    label = next((o['label'] for o in options if o['code'] == code), None)
    head = ('#%s %s' % (code, label)) if label else ''
    body = (free_text or '').strip()
    return (head + ('\n' + body if body else '')).strip()


def catalog():
    return {'reasons': REASONS, 'expectations': EXPECTATIONS,
            'metrics': METRICS, 'falsifiers': FALSIFIERS,
            'note': '選択肢は出発点であり、自由記述で必ず上書きできる。'
                    '選ばなかった項目を「該当なし」とは解釈しない。'}


if __name__ == '__main__':
    import json
    print(json.dumps(catalog(), ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""`fnd/` 財務スクリーニング実行器。ネットワーク取得もCSV変更も行わない。

`scr/`（20営業日の売買代金÷時価総額）は東証全銘柄の日次売買代金という一括取得が
必要で、現在の実行環境では母集団を揃えられない。`fnd/` は代わりに、EDINET等の
法定開示から銘柄単位で取得できる指標だけで候補を絞る。需給ではなく事業の実績で
探すので、`scr/` の代替ではなく別軸の入口である。

順位は「条件を満たした度合い」であり、投資評価・推奨・期待リターンではない。

  python3 app/fundscreen.py "fnd/"                                  # 必要データの一覧
  python3 app/fundscreen.py "fnd/ growth top=10" --input fnd.json --format markdown
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA_VERSION = 'fnd-input-v1'
MARKETS = ('prime', 'standard', 'growth')
MARKET_JA = {'prime': 'プライム', 'standard': 'スタンダード', 'growth': 'グロース'}

METRICS = {
    'revenueCagr3y': {'label': '売上CAGR3年', 'unit': '%', 'source': 'EDINET screen_companies / get_ranking: revenue-cagr-3y'},
    'operatingMargin': {'label': '営業利益率', 'unit': '%', 'source': 'EDINET screen_companies: operating-margin'},
    'operatingCf': {'label': '営業CF', 'unit': '百万円', 'source': 'EDINET screen_companies: cf-operating'},
    'equityRatio': {'label': '自己資本比率', 'unit': '%', 'source': 'EDINET screen_companies: equity-ratio'},
    'sharesChange5y': {'label': '発行済株式5年変化', 'unit': '%', 'source': 'EDINET get_ranking: shares-change-5y（希薄化）'},
    'roe': {'label': 'ROE', 'unit': '%', 'source': 'EDINET screen_companies: roe'},
    'fcfYield': {'label': 'FCF利回り', 'unit': '%', 'source': 'EDINET screen_companies: fcf-yield'},
    'netCashRatio': {'label': 'ネットキャッシュ比率', 'unit': '倍', 'source': 'EDINET screen_companies: net-cash-ratio'},
    'marketCapOku': {'label': '時価総額', 'unit': '億円', 'source': 'EDINET get_ranking: market-cap（有報の期末株価ベース。実勢とずれる）'},
}

PROFILES = {
    'tenbagger': {
        'label': '小型成長（3〜7年）',
        'required': ['revenueCagr3y', 'operatingMargin', 'operatingCf', 'equityRatio', 'sharesChange5y', 'marketCapOku'],
        'gates': [
            ('revenueCagr3y', 'gte', 15, '売上CAGR3年が15%未満'),
            ('operatingMargin', 'gte', 8, '営業利益率が8%未満'),
            ('operatingCf', 'gt', 0, '営業CFが黒字でない'),
            ('equityRatio', 'gte', 40, '自己資本比率が40%未満'),
            ('sharesChange5y', 'lte', 20, '5年で発行済株式が20%超増加（希薄化）'),
            ('marketCapOku', 'lte', 1500, '時価総額1500億円超（小型の範囲外）'),
        ],
        'score': [('revenueCagr3y', 1.0, False), ('operatingMargin', 1.0, False),
                  ('equityRatio', 0.5, False), ('sharesChange5y', 1.0, True)],
    },
    'quality': {
        'label': '高収益・低希薄化',
        'required': ['roe', 'operatingMargin', 'operatingCf', 'equityRatio', 'sharesChange5y', 'marketCapOku'],
        'gates': [
            ('roe', 'gte', 15, 'ROEが15%未満'),
            ('operatingMargin', 'gte', 10, '営業利益率が10%未満'),
            ('operatingCf', 'gt', 0, '営業CFが黒字でない'),
            ('equityRatio', 'gte', 50, '自己資本比率が50%未満'),
            ('sharesChange5y', 'lte', 0, '5年で発行済株式が増加'),
        ],
        'score': [('roe', 1.0, False), ('operatingMargin', 1.0, False), ('sharesChange5y', 0.5, True)],
    },
    'cash': {
        'label': 'ネットキャッシュ・FCF',
        'required': ['netCashRatio', 'fcfYield', 'operatingCf', 'equityRatio', 'marketCapOku'],
        'gates': [
            ('netCashRatio', 'gte', 0.5, 'ネットキャッシュ比率が0.5倍未満'),
            ('fcfYield', 'gte', 5, 'FCF利回りが5%未満'),
            ('operatingCf', 'gt', 0, '営業CFが黒字でない'),
        ],
        'score': [('netCashRatio', 1.0, False), ('fcfYield', 1.0, False)],
    },
}

OPS = {'gte': lambda a, b: a >= b, 'lte': lambda a, b: a <= b,
       'gt': lambda a, b: a > b, 'lt': lambda a, b: a < b}


class CommandError(ValueError):
    pass


def parse_command(text):
    """先頭行だけを解釈する。不明な引数は推測せずエラー。"""
    line = (text or '').strip().splitlines()[0].strip() if (text or '').strip() else ''
    if not line.lower().startswith('fnd/'):
        raise CommandError('先頭は fnd/ で始めてください')
    params = {'markets': list(MARKETS), 'top': 5, 'mincapOku': None, 'maxcapOku': None, 'profile': 'tenbagger'}
    seen = set()
    for token in line[4:].strip().split():
        key = token.lower()
        if key in MARKETS:
            if 'market' in seen:
                raise CommandError('市場は1つだけ指定できます')
            seen.add('market')
            params['markets'] = [key]
            continue
        if '=' not in token:
            raise CommandError('不明な引数です: ' + token)
        name, _, value = token.partition('=')
        name = name.lower()
        if name in seen:
            raise CommandError('引数が重複しています: ' + name)
        seen.add(name)
        if name == 'top':
            if not value.isdigit() or not 1 <= int(value) <= 50:
                raise CommandError('topは1〜50の整数です')
            params['top'] = int(value)
        elif name in ('mincap', 'maxcap'):
            try:
                num = float(value)
            except ValueError:
                raise CommandError(name + 'は数値（億円）です')
            if num < 0:
                raise CommandError(name + 'は0以上です')
            params[name + 'Oku'] = num
        elif name == 'profile':
            if value.lower() not in PROFILES:
                raise CommandError('profileは ' + ' / '.join(PROFILES) + ' です')
            params['profile'] = value.lower()
        else:
            raise CommandError('不明な引数です: ' + name)
    if params['mincapOku'] is not None and params['maxcapOku'] is not None and params['mincapOku'] > params['maxcapOku']:
        raise CommandError('mincapがmaxcapを超えています')
    return params


def requirements(params):
    profile = PROFILES[params['profile']]
    return {
        'schemaVersion': SCHEMA_VERSION,
        'status': 'DATA_REQUIRED',
        'parameters': params,
        'profile': {'key': params['profile'], 'label': profile['label'],
                    'gates': [{'metric': m, 'op': op, 'value': v, 'rejectReason': why}
                              for m, op, v, why in profile['gates']],
                    'scoreAxes': [{'metric': m, 'weight': w, 'lowerIsBetter': inv}
                                  for m, w, inv in profile['score']]},
        'requiredPerCandidate': ['code', 'name', 'market'] + profile['required'] + ['sourceIds', 'fiscalPeriod'],
        'metricGuide': {k: METRICS[k] for k in profile['required']},
        'rules': [
            '各指標は sourceIds[<metric>] に出典IDが必要。出典の無い値はUNKNOWNとして扱い、点数化しない。',
            '欠損を0で埋めない。必須指標が1つでも欠ければ dataRequired に落とし、順位に入れない。',
            '連結/単独、実績/予想、決算期を fiscalPeriod に明記する。混在した値を同じ列に入れない。',
            '順位は条件充足度であり、投資評価・推奨・期待リターンではない。',
            '母集団の網羅性を確認できない場合は coverageByMarket を PARTIAL とし「各市場TOP」と呼ばない。',
        ],
        'note': 'この実行器はネットワーク取得を行わない。出典付きの候補データを --input で渡すこと。',
    }


def _percentile(values, value, lower_is_better):
    if len(values) <= 1:
        return 50.0
    worse = sum(1 for v in values if (v > value if lower_is_better else v < value))
    ties = sum(1 for v in values if v == value)
    return round((worse + (ties - 1) / 2) / (len(values) - 1) * 100, 2)


def run(params, payload):
    if payload.get('schemaVersion') != SCHEMA_VERSION:
        raise CommandError('schemaVersionが %s ではありません' % SCHEMA_VERSION)
    profile = PROFILES[params['profile']]
    as_of = payload.get('asOf')
    if not as_of:
        raise CommandError('asOf（基準日）が必要です')
    coverage = payload.get('coverageByMarket') or {}
    candidates = payload.get('candidates') or []
    if not isinstance(candidates, list):
        raise CommandError('candidatesは配列です')

    data_required, excluded, ready = [], [], []
    seen = set()
    for c in candidates:
        code = str(c.get('code', '')).strip()
        market = str(c.get('market', '')).strip().lower()
        if not code or market not in MARKETS:
            data_required.append({'code': code or '(コードなし)', 'reason': '市場区分が prime/standard/growth ではありません'})
            continue
        if code in seen:
            raise CommandError('同じコードが重複しています: ' + code)
        seen.add(code)
        if market not in params['markets']:
            continue
        if c.get('securityType') and str(c['securityType']).lower() != 'common':
            excluded.append({'code': code, 'name': c.get('name', ''), 'market': market,
                             'reason': '普通株ではありません（%s）' % c['securityType']})
            continue
        sources = c.get('sourceIds') or {}
        values, missing = {}, []
        for metric in profile['required']:
            raw = c.get(metric)
            if raw is None or raw == '' or not sources.get(metric):
                missing.append(metric if raw not in (None, '') else metric)
                continue
            try:
                values[metric] = float(raw)
            except (TypeError, ValueError):
                missing.append(metric)
        if missing:
            data_required.append({'code': code, 'name': c.get('name', ''), 'market': market,
                                  'missing': sorted(set(missing)),
                                  'reason': '必須指標または出典IDが不足（0で埋めない）'})
            continue
        cap = values.get('marketCapOku')
        if cap is not None:
            if params['mincapOku'] is not None and cap < params['mincapOku']:
                excluded.append({'code': code, 'name': c.get('name', ''), 'market': market,
                                 'reason': '時価総額が下限未満（%g億円）' % cap})
                continue
            if params['maxcapOku'] is not None and cap > params['maxcapOku']:
                excluded.append({'code': code, 'name': c.get('name', ''), 'market': market,
                                 'reason': '時価総額が上限超（%g億円）' % cap})
                continue
        failed = [why for metric, op, threshold, why in profile['gates']
                  if metric in values and not OPS[op](values[metric], threshold)]
        if failed:
            excluded.append({'code': code, 'name': c.get('name', ''), 'market': market, 'reason': ' / '.join(failed)})
            continue
        ready.append({'code': code, 'name': c.get('name', ''), 'market': market,
                      'values': values, 'sourceIds': {k: sources[k] for k in profile['required']},
                      'fiscalPeriod': c.get('fiscalPeriod', 'UNKNOWN'),
                      'flags': c.get('flags', {}), 'note': c.get('note', '')})

    pools = {m: [r['values'][m] for r in ready] for m, _, _ in profile['score']}
    for r in ready:
        axes, total, weights = {}, 0.0, 0.0
        for metric, weight, inverse in profile['score']:
            pct = _percentile(pools[metric], r['values'][metric], inverse)
            axes[metric] = pct
            total += pct * weight
            weights += weight
        r['axes'] = axes
        r['score'] = round(total / weights, 2) if weights else 0.0
        r['investmentEvaluation'] = 'NOT_EVALUATED'

    ranking = {}
    for market in params['markets']:
        rows = sorted([r for r in ready if r['market'] == market],
                      key=lambda r: (-r['score'], r['code']))[:params['top']]
        for i, r in enumerate(rows, 1):
            r['rank'] = i
        ranking[market] = rows

    partial = any(coverage.get(m, 'UNKNOWN') != 'COMPLETE' for m in params['markets'])
    return {
        'schemaVersion': SCHEMA_VERSION,
        'status': 'PARTIAL' if partial else 'OK',
        'rankingScope': '取得済み範囲内順位' if partial else '各市場TOP',
        'asOf': as_of,
        'parameters': params,
        'profile': {'key': params['profile'], 'label': profile['label'],
                    'gates': [{'metric': m, 'op': op, 'value': v} for m, op, v, _ in profile['gates']],
                    'scoreAxes': [{'metric': m, 'weight': w, 'lowerIsBetter': inv} for m, w, inv in profile['score']]},
        'coverageByMarket': {m: coverage.get(m, 'UNKNOWN') for m in params['markets']},
        'counts': {'input': len(candidates), 'ranked': sum(len(v) for v in ranking.values()),
                   'passedGates': len(ready), 'excluded': len(excluded), 'dataRequired': len(data_required)},
        'ranking': ranking,
        'excluded': excluded,
        'dataRequired': data_required,
        'sources': payload.get('sources', []),
        'boundaries': [
            '順位は条件充足度であり、投資評価・買い順位・期待リターンではない。',
            'investmentEvaluation は全件 NOT_EVALUATED。財務の次に材料・競合・反対仮説を別工程で確認する。',
            'dataRequired の銘柄は「条件を満たさなかった」ではなく「判定できなかった」。',
            'この結果から PROPOSED / APPROVED / EXECUTED やCSV台帳の変更は生成しない。',
        ],
    }


def markdown(result):
    if result['status'] == 'DATA_REQUIRED':
        lines = ['# fnd/ 必要データ', '', '状態: DATA_REQUIRED（入力が無いため順位を作りません）', '',
                 '## 必須項目']
        for key, guide in result['metricGuide'].items():
            lines.append('- `%s` %s（%s）— %s' % (key, guide['label'], guide['unit'], guide['source']))
        lines += ['', '## 前提'] + ['- ' + r for r in result['rules']]
        return '\n'.join(lines)
    p = result['parameters']
    lines = ['# fnd/ %s' % result['profile']['label'], '',
             '基準日: %s ／ 状態: %s ／ 表示: %s' % (result['asOf'], result['status'], result['rankingScope']),
             '対象市場: %s ／ 上位: %d件 ／ 時価総額: %s〜%s億円' % (
                 '・'.join(MARKET_JA[m] for m in p['markets']), p['top'],
                 p['mincapOku'] if p['mincapOku'] is not None else '下限なし',
                 p['maxcapOku'] if p['maxcapOku'] is not None else '上限なし'),
             '母集団カバレッジ: %s' % ', '.join('%s=%s' % (MARKET_JA[k], v) for k, v in result['coverageByMarket'].items()),
             '件数: 入力%d / 条件通過%d / 除外%d / 判定不能%d' % (
                 result['counts']['input'], result['counts']['passedGates'],
                 result['counts']['excluded'], result['counts']['dataRequired']), '']
    axes = [m['metric'] for m in result['profile']['scoreAxes']]
    for market, rows in result['ranking'].items():
        lines.append('## %s' % MARKET_JA[market])
        if not rows:
            lines += ['', '該当なし。', '']
            continue
        header = ['順位', 'コード', '名称', '充足度'] + [METRICS[a]['label'] for a in axes] + ['決算期', '投資評価']
        lines.append('| ' + ' | '.join(header) + ' |')
        lines.append('|' + '---|' * len(header))
        for r in rows:
            cells = [str(r['rank']), r['code'], r['name'], '%.1f' % r['score']]
            cells += ['%g%s' % (r['values'][a], METRICS[a]['unit']) for a in axes]
            cells += [r['fiscalPeriod'], r['investmentEvaluation']]
            lines.append('| ' + ' | '.join(cells) + ' |')
        lines.append('')
    if result['dataRequired']:
        lines += ['## 判定不能（データ不足。条件を満たさなかったという意味ではない）']
        for d in result['dataRequired'][:50]:
            lines.append('- %s %s: %s' % (d.get('code'), d.get('name', ''), ', '.join(d.get('missing', [])) or d['reason']))
        lines.append('')
    if result['excluded']:
        lines += ['## 条件で除外']
        for d in result['excluded'][:50]:
            lines.append('- %s %s: %s' % (d.get('code'), d.get('name', ''), d['reason']))
        lines.append('')
    lines += ['## 境界'] + ['- ' + b for b in result['boundaries']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='fnd/ 財務スクリーニング（ネットワーク取得なし）')
    parser.add_argument('command')
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--format', choices=['json', 'markdown'], default='json')
    args = parser.parse_args(argv)
    try:
        params = parse_command(args.command)
        if args.input:
            result = run(params, json.loads(Path(args.input).read_text()))
        else:
            result = requirements(params)
    except CommandError as e:
        payload = {'status': 'ERROR', 'error': str(e)}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        print(text)
        return 2
    text = markdown(result) if args.format == 'markdown' else json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + '\n', encoding='utf-8')
        print('書き出しました: ' + args.output)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

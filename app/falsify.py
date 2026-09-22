#!/usr/bin/env python3
"""反証エンジン。撤回条件を機械可読にして、観測値で仮説を殴る。

theses.csv の falsifier 欄は今まで自由文だったので、誰も検査しなかった。
ここでは1行1条件の構文を読み、出典付きの観測値と突き合わせて
SUPPORTED / WATCH / CHALLENGED / UNTESTABLE を判定する。CSVは書き換えない。

  @falsify <指標> <演算子> <値> [単位] : <ラベル>      条件が成立したら仮説に反する
  @stale   <指標> <日数>d : <ラベル>                   観測がこの日数より古ければ要注視

  演算子: lt lte gt gte eq ne
  例:     @falsify 営業利益率 lt 10 % : 利益率が二桁を割る
          @falsify 増資 eq 1 : 希薄化を伴う公募増資
          @stale 営業CF 120d : 四半期開示を追えていない

使い方:
  python3 app/falsify.py audit                      # 撤回条件が検証可能かを点検
  python3 app/falsify.py template --output obs.json # 必要な観測値の一覧を出す
  python3 app/falsify.py run --input obs.json --output proposal.json
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from store import Store, number, validate, json_bytes, atomic  # noqa: E402
from insights import parse_date  # noqa: E402

SCHEMA_VERSION = 'falsify-input-v1'
OPS = {
    'lt': lambda a, b: a < b, 'lte': lambda a, b: a <= b,
    'gt': lambda a, b: a > b, 'gte': lambda a, b: a >= b,
    'eq': lambda a, b: a == b, 'ne': lambda a, b: a != b,
}
OP_TEXT = {'lt': '<', 'lte': '<=', 'gt': '>', 'gte': '>=', 'eq': '=', 'ne': '!='}
RULE = re.compile(r'@falsify\s+(?P<metric>\S+)\s+(?P<op>lt|lte|gt|gte|eq|ne)\s+(?P<value>-?[0-9.]+)\s*(?P<unit>[^\s:]*)\s*(?::\s*(?P<label>.*))?$')
STALE = re.compile(r'@stale\s+(?P<metric>\S+)\s+(?P<days>\d+)d\s*(?::\s*(?P<label>.*))?$')
STATUSES = ('UNREVIEWED', 'SUPPORTED', 'WATCH', 'CHALLENGED')


def parse_rules(text):
    """撤回条件の自由文から機械可読な条件だけを取り出す。読めない行は捨てずに返す。"""
    rules, unparsed = [], []
    for raw in (text or '').replace('；', ';').replace(';', '\n').splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith('@'):
            unparsed.append(line)
            continue
        m = RULE.match(line)
        if m:
            rules.append({'type': 'threshold', 'metric': m.group('metric'), 'op': m.group('op'),
                          'value': float(m.group('value')), 'unit': m.group('unit') or '',
                          'label': (m.group('label') or '').strip() or line})
            continue
        m = STALE.match(line)
        if m:
            rules.append({'type': 'stale', 'metric': m.group('metric'), 'days': int(m.group('days')),
                          'label': (m.group('label') or '').strip() or line})
            continue
        unparsed.append(line)
    return rules, unparsed


def audit(tables):
    """撤回条件が「検証可能な形で書かれているか」だけを見る。投資評価ではない。"""
    holdings = {h['id']: h for h in tables['holdings']}
    rows, metrics = [], set()
    for t in tables['theses']:
        rules, unparsed = parse_rules(t['falsifier'])
        for r in rules:
            metrics.add((t['holdingId'], r['metric']))
        if rules:
            state = 'TESTABLE'
        elif (t['falsifier'] or '').strip():
            state = 'TEXT_ONLY'
        else:
            state = 'EMPTY'
        rows.append({
            'thesisId': t['id'], 'holdingId': t['holdingId'],
            'name': holdings.get(t['holdingId'], {}).get('name', ''),
            'testability': state, 'ruleCount': len(rules),
            'rules': rules, 'unparsed': unparsed,
            'hasCounterCase': bool((t['counterCase'] or '').strip()),
            'thesisStatus': t['thesisStatus'],
        })
    counts = {}
    for r in rows:
        counts[r['testability']] = counts.get(r['testability'], 0) + 1
    return {'theses': rows, 'counts': counts,
            'requiredObservations': sorted([{'holdingId': h, 'metric': m} for h, m in metrics],
                                           key=lambda x: (x['holdingId'], x['metric'])),
            'note': 'TEXT_ONLY と EMPTY は「撤回条件が検証できない」状態であり、'
                    '仮説が正しいという意味ではない。'}


def template(state):
    result = audit(state['tables'])
    return {'schemaVersion': SCHEMA_VERSION, 'version': state['version'],
            'note': 'observationsは一次開示・発行体IR・市場データから取得し、sourceIdを必ず付ける。'
                    '推定値はquality=EST、取得できない項目は行ごと省略する（0で埋めない）。',
            'requiredObservations': result['requiredObservations'],
            'observations': [{'holdingId': o['holdingId'], 'metric': o['metric'], 'value': None,
                              'unit': '', 'asOf': None, 'sourceId': None, 'quality': 'FACT', 'note': ''}
                             for o in result['requiredObservations']],
            'testability': result['counts']}


def evaluate(tables, observations, at=None):
    at = at or datetime.now(timezone.utc)
    latest = {}
    for o in observations:
        key = (o.get('holdingId'), o.get('metric'))
        dt = parse_date(str(o.get('asOf') or ''))
        if dt is None or o.get('value') in (None, '') or not o.get('sourceId'):
            continue
        if key not in latest or dt > latest[key][0]:
            latest[key] = (dt, o)
    results = []
    for t in tables['theses']:
        rules, unparsed = parse_rules(t['falsifier'])
        verdicts = []
        for rule in rules:
            found = latest.get((t['holdingId'], rule['metric']))
            if found is None:
                verdicts.append({'rule': rule['label'], 'metric': rule['metric'],
                                 'verdict': 'UNKNOWN', 'detail': '出典付きの観測値がありません'})
                continue
            dt, obs = found
            age = max(0, (at - dt).days)
            if rule['type'] == 'stale':
                fired = age > rule['days']
                verdicts.append({'rule': rule['label'], 'metric': rule['metric'],
                                 'verdict': 'WATCH' if fired else 'PASS',
                                 'observed': obs['value'], 'asOf': obs['asOf'], 'ageDays': age,
                                 'sourceId': obs['sourceId'], 'quality': obs.get('quality', 'UNKNOWN'),
                                 'detail': '観測が%d日前（上限%d日）' % (age, rule['days'])})
                continue
            value = number(str(obs['value']))
            if value is None:
                verdicts.append({'rule': rule['label'], 'metric': rule['metric'],
                                 'verdict': 'UNKNOWN', 'detail': '観測値を数値として読めません'})
                continue
            fired = OPS[rule['op']](float(value), rule['value'])
            verdicts.append({
                'rule': rule['label'], 'metric': rule['metric'],
                'verdict': 'FIRED' if fired else 'PASS',
                'condition': '%s %s %g%s' % (rule['metric'], OP_TEXT[rule['op']], rule['value'], rule['unit']),
                'observed': obs['value'], 'asOf': obs['asOf'], 'ageDays': age,
                'sourceId': obs['sourceId'], 'quality': obs.get('quality', 'UNKNOWN'),
                'detail': '撤回条件が成立' if fired else '撤回条件は成立せず',
            })
        if not rules:
            status = 'UNREVIEWED'
            summary = 'UNTESTABLE: 機械可読な撤回条件がありません'
        elif any(v['verdict'] == 'FIRED' for v in verdicts):
            status = 'CHALLENGED'
            summary = '撤回条件が成立しました。保有の前提を再検討してください'
        elif any(v['verdict'] in ('UNKNOWN', 'WATCH') for v in verdicts):
            status = 'WATCH'
            summary = '検証できない条件が残っています。支持ではありません'
        elif any(v.get('quality') == 'EST' for v in verdicts):
            status = 'WATCH'
            summary = '推定値のみで判定しています。一次資料で再確認してください'
        else:
            status = 'SUPPORTED'
            summary = 'すべての撤回条件が出典付きの実績値で不成立でした'
        results.append({'thesisId': t['id'], 'holdingId': t['holdingId'],
                        'proposedStatus': status, 'currentStatus': t['thesisStatus'],
                        'summary': summary, 'verdicts': verdicts, 'unparsed': unparsed})
    counts = {}
    for r in results:
        counts[r['proposedStatus']] = counts.get(r['proposedStatus'], 0) + 1
    return {'evaluatedAt': at.isoformat(), 'results': results, 'counts': counts}


def propose(state, payload, at=None):
    if payload.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError('schemaVersionが %s ではありません' % SCHEMA_VERSION)
    if payload.get('version') != state['version']:
        raise ValueError('CONFLICT: 提案の元データが古くなっています。最新版を再読してください')
    at = at or datetime.now(timezone.utc)
    report = evaluate(state['tables'], payload.get('observations', []), at=at)
    tables = json.loads(json.dumps(state['tables']))
    by_id = {r['thesisId']: r for r in report['results']}
    stamp = at.astimezone(timezone(timedelta(hours=9))).replace(microsecond=0).isoformat()
    for row in tables['theses']:
        r = by_id.get(row['id'])
        if r is None or r['proposedStatus'] == 'UNREVIEWED':
            continue
        evidence = [v for v in r['verdicts'] if v.get('observed') is not None]
        if not evidence:
            continue
        row['thesisStatus'] = r['proposedStatus']
        row['latest'] = ' / '.join('%s=%s (%s)' % (v['metric'], v['observed'], v['asOf']) for v in evidence)[:1000]
        row['change'] = r['summary']
        row['reviewedAt'] = stamp
        sources = [v['sourceId'] for v in evidence if v.get('sourceId')]
        if sources:
            row['sourceId'] = sources[0]
    validate(tables)
    return tables, report


def main(argv=None):
    parser = argparse.ArgumentParser(description='反証エンジン（ネットワーク取得なし・CSV書き換えなし）')
    parser.add_argument('command', choices=['audit', 'template', 'run'])
    parser.add_argument('--input')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    store = Store()
    state = store.read()
    if args.command == 'audit':
        result = audit(state['tables'])
    elif args.command == 'template':
        result = template(state)
    else:
        if not args.input:
            raise SystemExit('--input が必要です')
        payload = json.loads(Path(args.input).read_text())
        tables, report = propose(state, payload)
        result = {'version': state['version'], 'tables': tables,
                  'changes': store.diff(state['tables'], tables),
                  'actor': 'AI', 'reason': payload.get('reason', '反証エンジンによる仮説状態の更新案'),
                  'status': 'PROPOSED', 'report': report}
    data = json_bytes(result)
    if args.output:
        atomic(Path(args.output), data)
        print('書き出しました: ' + args.output)
    else:
        print(data.decode('utf-8'))


if __name__ == '__main__':
    main()

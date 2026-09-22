#!/usr/bin/env python3
"""相場台帳（quotes.csv）ユーティリティ。ネットワーク取得は行わない。

保有台帳は「数量・取得原価・枠」という変化の遅い事実、相場は「価格・FX」という
変化の速い事実である。両者を同じ行に混ぜると、価格を1つ直すたびに正本を触ること
になる。ここでは出典付きの相場行を別に積み、保有台帳への反映は差分承認を通す。

  python3 app/quotes.py status
  python3 app/quotes.py template [--output quotes-input.json]
  python3 app/quotes.py ingest --input quotes-input.json --output proposal.json
"""
import argparse
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from store import Store, number, validate, json_bytes, atomic  # noqa: E402
from insights import quote_status, parse_date  # noqa: E402

SCHEMA_VERSION = 'quotes-input-v1'
QUOTE_FIELDS = 'id holdingId code kind value currency asOf retrievedAt quality sourceId note'.split()


def template(state):
    rows = []
    for h in state['tables']['holdings']:
        rows.append({
            'holdingId': h['id'], 'code': h['code'], 'name': h['name'],
            'kind': 'NAV' if h['scope'] == 'ideco' else 'PRICE',
            'currency': h['currency'], 'value': None, 'asOf': None,
            'retrievedAt': None, 'quality': 'FACT', 'sourceId': None,
            'pnlJpy': None if h['scope'] == 'ideco' else 'n/a',
        })
    return {
        'schemaVersion': SCHEMA_VERSION,
        'version': state['version'],
        'note': 'asOf・retrievedAtはISO形式のみ（例 2026-09-18T15:30:00+09:00）。'
                'valueは取得した相場そのもの。円換算の逆算で埋めない。'
                'iDeCoはkind=NAVで評価額（円）を入れ、pnlJpyも同時点の報告値を入れる。'
                'pnlJpyが無いiDeCo行は反映しない（古い損益を残さないため）。',
        'requiredPerRow': ['holdingId or code', 'kind', 'value', 'currency', 'asOf', 'sourceId'],
        'fx': [{'code': 'USDJPY', 'value': None, 'asOf': None, 'retrievedAt': None,
                'quality': 'FACT', 'sourceId': None}],
        'sources': [{'id': 'SRC_QUOTE_YYYYMMDD', 'kind': 'MARKET_DATA', 'title': None,
                     'uri': None, 'publishedAt': None, 'retrievedAt': None,
                     'dataAsOf': None, 'confidence': 'SINGLE_SOURCE', 'note': ''}],
        'quotes': rows,
    }


def _row(prefix, index, data):
    row = {k: '' for k in QUOTE_FIELDS}
    row.update({k: str(v) for k, v in data.items() if v is not None})
    row['id'] = data.get('id') or '%s%04d' % (prefix, index)
    return row


def ingest(state, payload, at_ids=None):
    """相場行を積み、保有台帳への反映案（PROPOSED）を作る。保存はしない。"""
    if payload.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError('schemaVersionが %s ではありません' % SCHEMA_VERSION)
    if payload.get('version') != state['version']:
        raise ValueError('CONFLICT: 提案の元データが古くなっています。最新版を再読してください')
    tables = json.loads(json.dumps(state['tables']))
    holdings = {h['id']: h for h in tables['holdings']}
    source_ids = {s['id'] for s in tables['sources']}
    for src in payload.get('sources', []):
        if src['id'] in source_ids:
            continue
        row = {k: '' for k in ('id kind title uri publishedAt retrievedAt dataAsOf confidence note'.split())}
        row.update({k: str(v) for k, v in src.items() if v is not None})
        tables['sources'].append(row)
        source_ids.add(row['id'])

    existing = len(tables['quotes'])
    report = {'applied': [], 'skipped': [], 'fx': [], 'quoteRows': 0}

    fx_map = {}
    seq = 0
    for f in payload.get('fx', []) or []:
        if f.get('value') in (None, '') or not f.get('asOf') or not f.get('sourceId'):
            report['skipped'].append({'target': f.get('code'), 'reason': 'FXの値・基準日時・出典が揃っていません'})
            continue
        seq += 1
        row = _row('Q', existing + seq, {**f, 'kind': 'FX', 'currency': 'JPY', 'holdingId': ''})
        row['code'] = str(f['code']).upper()
        tables['quotes'].append(row)
        fx_map[row['code']] = number(row['value'])
        report['fx'].append({'code': row['code'], 'value': row['value'], 'asOf': row['asOf']})

    for q in payload.get('quotes', []) or []:
        hid = q.get('holdingId')
        if q.get('value') in (None, '') or not q.get('asOf') or not q.get('sourceId'):
            report['skipped'].append({'target': hid or q.get('code'), 'reason': '値・基準日時・出典のいずれかが未入力'})
            continue
        if hid not in holdings:
            report['skipped'].append({'target': hid, 'reason': '保有IDが見つかりません'})
            continue
        h = holdings[hid]
        kind = q.get('kind') or ('NAV' if h['scope'] == 'ideco' else 'PRICE')
        currency = q.get('currency') or h['currency']
        seq += 1
        row = _row('Q', existing + seq, {**q, 'kind': kind, 'currency': currency, 'holdingId': hid})
        row.pop('pnlJpy', None)
        row = {k: row.get(k, '') for k in QUOTE_FIELDS}
        tables['quotes'].append(row)

        value = number(row['value'])
        if kind == 'NAV':
            pnl = q.get('pnlJpy')
            if pnl in (None, '', 'n/a'):
                report['skipped'].append({'target': hid, 'reason': 'iDeCoは同時点の報告損益が無いと反映しない'})
                continue
            h['marketValueJpy'] = str(int(Decimal(str(value)).quantize(Decimal('1'), ROUND_HALF_UP)))
            h['pnlJpy'] = str(int(Decimal(str(pnl)).quantize(Decimal('1'), ROUND_HALF_UP)))
            h['priceAsOf'] = str(row['asOf'])
            h['sourceId'] = row['sourceId']
            report['applied'].append({'holdingId': hid, 'field': 'marketValueJpy', 'value': h['marketValueJpy']})
            continue
        if currency == 'JPY':
            fx = Decimal('1')
        else:
            pair = (currency + 'JPY').upper()
            if pair not in fx_map:
                report['skipped'].append({'target': hid, 'reason': '%s のFXが同じ入力に無い' % pair})
                continue
            fx = Decimal(str(fx_map[pair]))
        qty = number(h['quantity'])
        if qty is None:
            report['skipped'].append({'target': hid, 'reason': '数量が未登録のため評価額を再計算しない'})
            continue
        market = (Decimal(str(value)) * Decimal(str(qty)) * fx).quantize(Decimal('1'), ROUND_HALF_UP)
        h['price'] = str(value)
        h['fx'] = str(fx)
        h['priceAsOf'] = str(row['asOf'])
        h['marketValueJpy'] = str(int(market))
        cost = number(h['costBasisJpy'])
        h['pnlJpy'] = str(int(market - Decimal(str(cost)))) if cost is not None else ''
        h['sourceId'] = row['sourceId']
        report['applied'].append({'holdingId': hid, 'price': h['price'], 'fx': h['fx'],
                                  'marketValueJpy': h['marketValueJpy'], 'pnlJpy': h['pnlJpy'] or 'UNKNOWN'})

    report['quoteRows'] = len(tables['quotes']) - existing
    validate(tables)
    return tables, report


def main(argv=None):
    parser = argparse.ArgumentParser(description='相場台帳ユーティリティ（ネットワーク取得なし）')
    parser.add_argument('command', choices=['status', 'template', 'ingest'])
    parser.add_argument('--input')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    store = Store()
    state = store.read()
    if args.command == 'status':
        result = quote_status(state['tables'])
    elif args.command == 'template':
        result = template(state)
    else:
        if not args.input:
            raise SystemExit('--input が必要です')
        payload = json.loads(Path(args.input).read_text())
        tables, report = ingest(state, payload)
        proposal = {'version': state['version'], 'tables': tables,
                    'changes': store.diff(state['tables'], tables),
                    'actor': 'AI', 'reason': payload.get('reason', '出典付き相場の反映案'),
                    'status': 'PROPOSED', 'report': report}
        result = proposal
    data = json_bytes(result)
    if args.output:
        atomic(Path(args.output), data)
        print('書き出しました: ' + args.output)
    else:
        print(data.decode('utf-8'))


if __name__ == '__main__':
    main()

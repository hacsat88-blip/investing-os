"""v4.4追加機能（fnd/・反証エンジン・相場台帳）の受入テスト。"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

def _find_root(start):
    """app/store.py を持つ最初の親を探す。tests/ の配置が変わっても壊れない。"""
    for d in [start, *start.parents]:
        if (d / 'app' / 'store.py').is_file():
            return d
    raise RuntimeError('app/store.py が見つかりません: ' + str(start))


ROOT = _find_root(Path(__file__).resolve().parent)
FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'data'
sys.path.insert(0, str(ROOT / 'app'))

import catalog  # noqa: E402
import fundscreen  # noqa: E402
import falsify  # noqa: E402
import quotes as quotes_cli  # noqa: E402
from store import Store, validate, SCHEMAS  # noqa: E402
from insights import quote_status  # noqa: E402

AT = datetime(2026, 9, 20, 3, 0, tzinfo=timezone.utc)


def candidate(code, **over):
    base = {'code': code, 'name': code, 'market': 'growth', 'securityType': 'common',
            'revenueCagr3y': 30.0, 'operatingMargin': 20.0, 'operatingCf': 500.0,
            'equityRatio': 60.0, 'sharesChange5y': 2.0, 'marketCapOku': 200.0,
            'fiscalPeriod': '有報・連結・実績',
            'sourceIds': {k: 'S1' for k in ('revenueCagr3y', 'operatingMargin', 'operatingCf',
                                            'equityRatio', 'sharesChange5y', 'marketCapOku')}}
    base.update(over)
    return base


def payload(*cands, coverage='PARTIAL'):
    return {'schemaVersion': 'fnd-input-v1', 'asOf': '2026-09-20',
            'coverageByMarket': {'growth': coverage, 'prime': coverage, 'standard': coverage},
            'candidates': list(cands)}


class CommandTests(unittest.TestCase):
    def test_defaults(self):
        p = fundscreen.parse_command('fnd/')
        self.assertEqual(p['markets'], list(fundscreen.MARKETS))
        self.assertEqual((p['top'], p['profile']), (5, 'tenbagger'))

    def test_arguments(self):
        p = fundscreen.parse_command('fnd/ growth top=10 mincap=100 maxcap=1000 profile=quality')
        self.assertEqual(p['markets'], ['growth'])
        self.assertEqual((p['top'], p['mincapOku'], p['maxcapOku'], p['profile']), (10, 100.0, 1000.0, 'quality'))

    def test_only_first_line_and_rejections(self):
        p = fundscreen.parse_command('fnd/ prime\n本文中の fnd/ growth は無視する')
        self.assertEqual(p['markets'], ['prime'])
        for bad in ('scr/', 'fnd/ unknown=1', 'fnd/ top=0', 'fnd/ top=51',
                    'fnd/ mincap=1000 maxcap=100', 'fnd/ prime growth', 'fnd/ top=3 top=4',
                    'fnd/ profile=none'):
            with self.assertRaises(fundscreen.CommandError, msg=bad):
                fundscreen.parse_command(bad)

    def test_requirements_without_input(self):
        req = fundscreen.requirements(fundscreen.parse_command('fnd/'))
        self.assertEqual(req['status'], 'DATA_REQUIRED')
        self.assertIn('marketCapOku', req['requiredPerCandidate'])


class ScreeningTests(unittest.TestCase):
    def test_missing_metric_is_not_zero(self):
        c = candidate('1111')
        c.pop('operatingCf')
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'), payload(c))
        self.assertEqual(result['counts']['dataRequired'], 1)
        self.assertEqual(result['ranking']['growth'], [])
        self.assertIn('operatingCf', result['dataRequired'][0]['missing'])

    def test_missing_source_id_is_data_required(self):
        c = candidate('1111')
        c['sourceIds'].pop('equityRatio')
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'), payload(c))
        self.assertEqual(result['counts']['dataRequired'], 1)

    def test_gate_exclusion_and_non_common(self):
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'), payload(
            candidate('1111', operatingCf=-1),
            candidate('2222', sharesChange5y=45),
            candidate('3333', securityType='reit'),
            candidate('4444')))
        self.assertEqual(result['counts']['ranked'], 1)
        self.assertEqual(result['ranking']['growth'][0]['code'], '4444')
        self.assertEqual(len(result['excluded']), 3)

    def test_market_cap_band(self):
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth mincap=100 maxcap=300'), payload(
            candidate('1111', marketCapOku=50), candidate('2222', marketCapOku=200),
            candidate('3333', marketCapOku=900)))
        self.assertEqual([r['code'] for r in result['ranking']['growth']], ['2222'])

    def test_partial_scope_and_tie_break(self):
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'),
                                payload(candidate('2222'), candidate('1111')))
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['rankingScope'], '取得済み範囲内順位')
        self.assertEqual([r['code'] for r in result['ranking']['growth']], ['1111', '2222'])

    def test_complete_coverage_label(self):
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'),
                                payload(candidate('1111'), coverage='COMPLETE'))
        self.assertEqual(result['rankingScope'], '各市場TOP')

    def test_ranking_is_not_investment_evaluation(self):
        result = fundscreen.run(fundscreen.parse_command('fnd/ growth'), payload(candidate('1111')))
        row = result['ranking']['growth'][0]
        self.assertEqual(row['investmentEvaluation'], 'NOT_EVALUATED')
        blob = json.dumps(result, ensure_ascii=False)
        for forbidden in ('"PROPOSED"', '"APPROVED"', '"EXECUTED"', 'CSV_SYNCED'):
            self.assertNotIn(forbidden, blob)

    def test_duplicate_code_rejected(self):
        with self.assertRaises(fundscreen.CommandError):
            fundscreen.run(fundscreen.parse_command('fnd/ growth'),
                           payload(candidate('1111'), candidate('1111')))

    def test_as_of_required(self):
        body = payload(candidate('1111'))
        body.pop('asOf')
        with self.assertRaises(fundscreen.CommandError):
            fundscreen.run(fundscreen.parse_command('fnd/ growth'), body)


class FalsifyTests(unittest.TestCase):
    def tables(self, falsifier, status='UNREVIEWED'):
        return {'holdings': [{'id': 'H1', 'name': 'テスト'}],
                'theses': [{'id': 'TH1', 'holdingId': 'H1', 'falsifier': falsifier,
                            'counterCase': '', 'thesisStatus': status}]}

    def test_rule_parsing(self):
        rules, unparsed = falsify.parse_rules(
            '@falsify 営業利益率 lt 10 % : 二桁割れ; @stale 営業CF 120d; 自由文は残す')
        self.assertEqual([r['type'] for r in rules], ['threshold', 'stale'])
        self.assertEqual(unparsed, ['自由文は残す'])

    def test_fired_rule_challenges_thesis(self):
        r = falsify.evaluate(self.tables('@falsify 営業利益率 lt 10 %'),
                             [{'holdingId': 'H1', 'metric': '営業利益率', 'value': 8,
                               'asOf': '2026-08-01', 'sourceId': 'S1', 'quality': 'FACT'}], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'CHALLENGED')

    def test_passed_rule_supports_only_with_fact(self):
        obs = {'holdingId': 'H1', 'metric': '営業利益率', 'value': 15,
               'asOf': '2026-08-01', 'sourceId': 'S1', 'quality': 'FACT'}
        r = falsify.evaluate(self.tables('@falsify 営業利益率 lt 10 %'), [obs], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'SUPPORTED')
        r = falsify.evaluate(self.tables('@falsify 営業利益率 lt 10 %'),
                             [dict(obs, quality='EST')], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'WATCH')

    def test_missing_observation_is_watch_not_supported(self):
        r = falsify.evaluate(self.tables('@falsify 営業利益率 lt 10 %'), [], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'WATCH')

    def test_observation_without_source_is_ignored(self):
        r = falsify.evaluate(self.tables('@falsify 営業利益率 lt 10 %'),
                             [{'holdingId': 'H1', 'metric': '営業利益率', 'value': 8,
                               'asOf': '2026-08-01', 'sourceId': '', 'quality': 'FACT'}], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'WATCH')

    def test_stale_rule(self):
        r = falsify.evaluate(self.tables('@stale 営業CF 30d'),
                             [{'holdingId': 'H1', 'metric': '営業CF', 'value': 100,
                               'asOf': '2026-01-01', 'sourceId': 'S1', 'quality': 'FACT'}], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'WATCH')

    def test_text_only_falsifier_is_untestable(self):
        result = falsify.audit(self.tables('業績が悪化したら売る'))
        self.assertEqual(result['counts'], {'TEXT_ONLY': 1})
        r = falsify.evaluate(self.tables('業績が悪化したら売る'), [], at=AT)
        self.assertEqual(r['results'][0]['proposedStatus'], 'UNREVIEWED')
        self.assertIn('UNTESTABLE', r['results'][0]['summary'])


class CatalogTests(unittest.TestCase):
    def test_every_template_generates_a_machine_readable_rule(self):
        for tpl in catalog.FALSIFIERS:
            line = catalog.rule_line(tpl['code'])
            rules, unparsed = falsify.parse_rules(line)
            self.assertEqual(len(rules), 1, tpl['code'])
            self.assertEqual(unparsed, [], tpl['code'])
            self.assertEqual(rules[0]['metric'], tpl['metric'])

    def test_custom_threshold_and_negative_values(self):
        line = catalog.rule_line('DRAWDOWN', -30)
        rules, _ = falsify.parse_rules(line)
        self.assertEqual((rules[0]['op'], rules[0]['value']), ('lte', -30.0))
        stale, _ = falsify.parse_rules(catalog.rule_line('REVIEW_STALE', 45))
        self.assertEqual((stale[0]['type'], stale[0]['days']), ('stale', 45))

    def test_unknown_template_and_bad_value_rejected(self):
        with self.assertRaises(ValueError):
            catalog.rule_line('NOT_A_TEMPLATE')
        with self.assertRaises(ValueError):
            catalog.rule_line('OP_MARGIN', 'たぶん10%くらい')

    def test_suggestions_reference_existing_codes(self):
        metrics = {m['code'] for m in catalog.METRICS}
        falsifiers = {f['code'] for f in catalog.FALSIFIERS}
        for reason in catalog.REASONS:
            for m in reason['suggestMetrics']:
                self.assertIn(m, metrics, reason['code'])
            for f in reason['suggestFalsifiers']:
                self.assertIn(f, falsifiers, reason['code'])
        for tpl in catalog.FALSIFIERS:
            self.assertIn(tpl['metric'], metrics, tpl['code'])

    def test_tagged_keeps_free_text_and_is_reversible(self):
        text = catalog.tagged('GROWTH_TOPLINE', catalog.REASONS, '電力インフラの更新需要')
        self.assertTrue(text.startswith('#GROWTH_TOPLINE '))
        self.assertIn('電力インフラの更新需要', text)
        self.assertEqual(catalog.tagged('', catalog.REASONS, '分類なしの自由記述'), '分類なしの自由記述')

    def test_catalog_payload_shape(self):
        data = catalog.catalog()
        self.assertEqual(set(data) >= {'reasons', 'expectations', 'metrics', 'falsifiers'}, True)
        self.assertGreaterEqual(len(data['reasons']), 8)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='investingos-test-'))
        self.addCleanup(shutil.rmtree, self.dir, True)
        # 実データではなく固定フィクスチャを使う。運用台帳が変わってもテストは動く。
        shutil.copytree(FIXTURE, self.dir / 'data')
        self.store = Store(self.dir)
        self.state = self.store.read()

    def test_legacy_revision_reads_quotes_as_empty(self):
        self.assertIn('quotes', SCHEMAS)
        self.assertEqual(self.state['tables']['quotes'], [])

    def test_quote_validation(self):
        good = {'id': 'Q1', 'holdingId': 'H001', 'code': '5803', 'kind': 'PRICE', 'value': '4982',
                'currency': 'JPY', 'asOf': '2026-09-18T15:30:00+09:00', 'retrievedAt': '',
                'quality': 'FACT', 'sourceId': 'SRC_IMPORT_20260912', 'note': ''}
        tables = dict(self.state['tables'], quotes=[good])
        validate(tables)
        for broken in ({'value': '0'}, {'value': '-5'}, {'sourceId': ''}, {'asOf': ''},
                       {'asOf': '2026-09-18 close'}, {'kind': 'GUESS'}, {'quality': 'GOOD'},
                       {'holdingId': 'H999'}, {'currency': 'EUR'}):
            with self.assertRaises(ValueError, msg=str(broken)):
                validate(dict(self.state['tables'], quotes=[dict(good, **broken)]))
        with self.assertRaises(ValueError):
            validate(dict(self.state['tables'], quotes=[good, dict(good, id='Q2')]))
        with self.assertRaises(ValueError):
            validate(dict(self.state['tables'], quotes=[dict(good, kind='FX', code='USDJPY')]))

    def test_ingest_recomputes_and_fails_closed(self):
        body = {'schemaVersion': 'quotes-input-v1', 'version': self.state['version'],
                'sources': [{'id': 'SQ', 'kind': 'MARKET_DATA', 'title': 't', 'uri': 'u',
                             'retrievedAt': '2026-09-20T12:00:00+09:00', 'dataAsOf': '2026-09-18',
                             'confidence': 'SINGLE_SOURCE', 'note': ''}],
                'fx': [],
                'quotes': [
                    {'holdingId': 'H001', 'kind': 'PRICE', 'value': 5100, 'currency': 'JPY',
                     'asOf': '2026-09-18T15:30:00+09:00', 'quality': 'FACT', 'sourceId': 'SQ'},
                    {'holdingId': 'H007', 'kind': 'PRICE', 'value': 33.1, 'currency': 'USD',
                     'asOf': '2026-09-18T15:30:00+09:00', 'quality': 'FACT', 'sourceId': 'SQ'},
                    {'holdingId': 'H009', 'kind': 'NAV', 'value': 1300000, 'currency': 'JPY',
                     'asOf': '2026-09-18T22:40:00+09:00', 'quality': 'EST', 'sourceId': 'SQ'}]}
        tables, report = quotes_cli.ingest(self.state, body)
        applied = {a['holdingId'] for a in report['applied']}
        self.assertEqual(applied, {'H001'})
        skipped = {s['target']: s['reason'] for s in report['skipped']}
        self.assertIn('USDJPY', skipped['H007'])
        self.assertIn('報告損益', skipped['H009'])
        h1 = next(r for r in tables['holdings'] if r['id'] == 'H001')
        self.assertEqual((h1['price'], h1['marketValueJpy'], h1['pnlJpy']), ('5100', '10200', '-250'))
        h7 = next(r for r in tables['holdings'] if r['id'] == 'H007')
        self.assertEqual(h7['price'], self.state['tables']['holdings'][6]['price'])
        self.assertEqual(len(tables['quotes']), 3)

    def test_ingest_rejects_stale_version(self):
        with self.assertRaises(ValueError):
            quotes_cli.ingest(self.state, {'schemaVersion': 'quotes-input-v1',
                                           'version': 'x' * 32, 'quotes': []})

    def test_quote_status_flags(self):
        tables = dict(self.state['tables'], quotes=[
            {'id': 'Q1', 'holdingId': 'H001', 'code': '5803', 'kind': 'PRICE', 'value': '6000',
             'currency': 'JPY', 'asOf': '2026-09-18T15:30:00+09:00', 'retrievedAt': '',
             'quality': 'FACT', 'sourceId': 'SRC_IMPORT_20260912', 'note': ''}])
        result = quote_status(tables, at=AT)
        row = next(r for r in result['holdings'] if r['holdingId'] == 'H001')
        self.assertEqual(row['status'], 'MISMATCH')
        self.assertEqual(result['counts']['NO_QUOTE'], 9)

    def test_commit_writes_schema_44_and_keeps_decisions_append_only(self):
        tables = json.loads(json.dumps(self.state['tables']))
        tables['quotes'].append({'id': 'Q1', 'holdingId': 'H001', 'code': '5803', 'kind': 'PRICE',
                                 'value': '5100', 'currency': 'JPY',
                                 'asOf': '2026-09-18T15:30:00+09:00', 'retrievedAt': '',
                                 'quality': 'FACT', 'sourceId': 'SRC_IMPORT_20260912', 'note': ''})
        saved = self.store.commit(tables, self.state['version'], 'AI', '相場台帳の追加テスト')
        self.assertEqual(saved['meta']['schemaVersion'], '4.4')
        self.assertEqual(len(saved['tables']['quotes']), 1)
        reread = Store(self.dir).read()
        self.assertEqual(len(reread['tables']['quotes']), 1)
        with_decision = json.loads(json.dumps(reread['tables']))
        with_decision['decisions'].append({
            'id': 'D1', 'code': '5803', 'asOf': '2026-09-20', 'status': 'PROPOSED',
            'proposal': '追加検討', 'approvalEvidence': '', 'executionEvidence': '',
            'sourceId': 'SRC_IMPORT_20260912', 'note': ''})
        after = self.store.commit(with_decision, reread['version'], 'AI', '判断履歴の追記')
        broken = json.loads(json.dumps(after['tables']))
        broken['decisions'] = []
        with self.assertRaises(ValueError):
            self.store.commit(broken, after['version'], 'AI', '判断履歴の削除は拒否されるべき')
        rewritten = json.loads(json.dumps(after['tables']))
        rewritten['decisions'][0]['proposal'] = '書き換え'
        with self.assertRaises(ValueError):
            self.store.commit(rewritten, after['version'], 'AI', '判断履歴の改変は拒否されるべき')


if __name__ == '__main__':
    unittest.main()

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'outputs/investingOS-v4.2'
sys.path.insert(0,str(ROOT/'app'))
from store import Store, SCHEMAS, csv_bytes, digest, validate
from insights import risks,simulate,compare,research_queue,health

class V43(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name));self.t=copy.deepcopy(Store(ROOT).read()['tables']);self.state=self.s.commit(self.t,None,'MIGRATION','test')
 def tearDown(self):self.tmp.cleanup()
 def row(self,table,**v):
  r={k:'' for k in SCHEMAS[table]};r.update(sourceId='SRC43_REQUEST');r.update(v);return r
 def test_migration_preserves_core(self):
  before=json.loads((ROOT/'audit/before-v4.3.json').read_text())
  live=Store(ROOT).read()
  for key in ('holdings','targets','decisions'):self.assertEqual(live['meta']['hashes'][key],before['hashes'][key])
  old=Store(ROOT).read_revision(before['version']);self.assertEqual(old['tables']['theses'],[])
 def test_thesis_persistence_and_conflict(self):
  self.t['theses'][0]['reason']='Test reason';saved=self.s.commit(self.t,self.state['version'],'USER','test reason')
  self.assertEqual(self.s.read()['tables']['theses'][0]['reason'],'Test reason')
  with self.assertRaisesRegex(ValueError,'CONFLICT'):self.s.commit(self.t,self.state['version'],'AI','stale')
  self.s.commit(self.s.restore_tables(self.state['version']),saved['version'],'RESTORE','restore')
  self.assertEqual(self.s.read()['tables']['theses'][0]['reason'],'')
 def test_research_order_reacts(self):
  a,b=self.t['research'][:2]
  a.update(impact='1',uncertainty='1',urgency='1',effort='1')
  b.update(impact='5',uncertainty='5',urgency='5',effort='5')
  self.assertEqual(research_queue(self.t)[0]['id'],b['id'])
  b['researchStatus']='DONE';self.assertEqual(research_queue(self.t)[0]['id'],a['id'])
  self.t['research'][2]['dueOn']='2026-01-01';self.assertEqual(research_queue(self.t)[0]['id'],self.t['research'][2]['id'])
 def test_partial_lookthrough_no_renormalization(self):
  self.t['exposures']=[self.row('exposures',id='E1',holdingId='H009',dimension='ISSUER',component='ACME',weight='0.1',asOf='2026-08-29',quality='EST')]
  validate(self.t);d=risks(self.t)['dimensions']['ISSUER'];self.assertAlmostEqual(d['covered'],126781.8);self.assertLess(d['coverage'],0.1)
  self.assertGreater(d['unmappedKnown'],3900000)
  self.t['exposures'].append(self.row('exposures',id='E2',holdingId='H009',dimension='ISSUER',component='OTHER',weight='0.95',asOf='2026-08-29',quality='FACT'))
  with self.assertRaises(ValueError):validate(self.t)
 def test_stress_cross_effect_and_missing(self):
  r=simulate(self.t,-20,-10);usd=r['rows'][6];self.assertAlmostEqual(usd['after'],usd['before']*.8*.9)
  self.assertAlmostEqual(r['rows'][0]['after'],r['rows'][0]['before']*.8)
  with self.assertRaises(ValueError):simulate(self.t,'','-10')
  with self.assertRaises(ValueError):simulate(self.t,'NaN',0)
  self.t['holdings'][0]['price']='';self.assertEqual(simulate(self.t,0,0)['missing'],1)
 def test_compare_budget_stale_tax_and_no_mutation(self):
  original=copy.deepcopy(self.t['holdings']);plan=self.t['plans'][1];plan.update(additionalCashJpy='10000',feesJpy='100',taxJpy='0')
  self.t['plan_items']=[self.row('plan_items',id='I1',planId=plan['id'],holdingId='H001',targetValueJpy='14964')]
  result=compare(self.t)['results'][1];self.assertTrue(result['ready']);self.assertAlmostEqual(result['cash'],4900)
  self.assertEqual(self.t['holdings'],original)
  plan['taxJpy']='';self.assertFalse(compare(self.t)['results'][1]['ready'])
  plan['taxJpy']='0';self.t['plan_items'][0]['targetValueJpy']='100000000';self.assertFalse(compare(self.t)['results'][1]['ready'])
  plan['baselineHash']='old';self.assertFalse(compare(self.t)['results'][1]['ready'])
 def test_health_no_false_success(self):
  h=health(self.s,self.state);self.assertEqual(h['monitoring']['status'],'UNVERIFIED');self.assertEqual(h['backup'],'VERIFIED');self.assertIsNone(h['confirmations']['NOTIFICATION'])
  m=self.s.root/'monitoring';m.mkdir();(m/'state.json').write_text(json.dumps({'lastStatus':'SUCCESS','lastAttemptAt':'2026-09-13T09:05:00+09:00','reportPath':'missing.md'}))
  self.assertEqual(health(self.s,self.state)['monitoring']['status'],'UNVERIFIED')
  (m/'report.md').write_text('test evidence');(m/'state.json').write_text(json.dumps({'lastStatus':'PARTIAL','lastAttemptAt':'2026-09-13T09:05:00+09:00','reportPath':'report.md'}))
  self.assertEqual(health(self.s,self.state)['monitoring']['status'],'PARTIAL')
  (self.s.root/'backups'/(self.state['version']+'.zip')).write_bytes(b'broken')
  self.assertEqual(health(self.s,self.state)['backup'],'FAILED')
 def test_reference_checks(self):
  self.t['theses'][0]['holdingId']='missing'
  with self.assertRaises(ValueError):validate(self.t)
  self.t['theses'][0]['holdingId']='H001';self.t['research'][0]['impact']='6'
  with self.assertRaises(ValueError):validate(self.t)

if __name__=='__main__':unittest.main(verbosity=2)

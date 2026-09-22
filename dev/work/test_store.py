import copy
import csv
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'outputs/investingOS-v4.2'
sys.path.insert(0,str(ROOT/'app'))
from store import Store, validate, summary, digest

class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.s=Store(self.root)
        self.initial=Store(ROOT).read()['tables']
        self.state=self.s.commit(self.initial,None,'MIGRATION','test seed')
    def tearDown(self):
        self.tmp.cleanup()
    def test_source_preservation(self):
        with (ROOT/'reference/investingOS_ChatGPT/exports/holdings_2026-09-12.csv').open(encoding='utf-8-sig',newline='') as f:
            original=list(csv.DictReader(f))
        self.assertEqual(len(original),10)
        for a,b in zip(original,self.state['tables']['holdings']):
            self.assertEqual(a,{k:b[k] for k in a})
        self.assertEqual(self.state['tables']['holdings'][1]['code'],'285A')
    def test_missing_values(self):
        s=self.state['summary']
        self.assertEqual(s['pnlMissing'],1)
        self.assertEqual(len(s['dates']),2)
        self.assertIsNone(s['rows'][6]['pnl'])
        self.assertAlmostEqual(s['subtotal'],4120281.557796,places=4)
    def test_conflict_and_backups(self):
        t=copy.deepcopy(self.initial);t['holdings'][0]['note']='User edit'
        saved=self.s.commit(t,self.state['version'],'USER','manual note')
        with self.assertRaisesRegex(ValueError,'CONFLICT'):
            self.s.commit(self.initial,self.state['version'],'AI','stale')
        self.assertEqual(self.s.read()['version'],saved['version'])
        zpath=self.root/'backups'/(saved['version']+'.zip')
        with zipfile.ZipFile(zpath) as z:
            meta=json.loads(z.read('manifest.json'))
            for table in self.initial:
                self.assertEqual(digest(z.read(table+'.csv')),meta['hashes'][table])
        restored=self.s.commit(self.s.restore_tables(self.state['version']),saved['version'],'RESTORE','restore')
        self.assertEqual(restored['tables'],self.initial)
        self.assertEqual(len(self.s.history()),3)
    def test_reject_bad_data(self):
        for field,value in [('quantity','NaN'),('quantity','-1'),('fx','0'),('note','=HYPERLINK("bad")'),('sourceId','missing')]:
            t=copy.deepcopy(self.initial);t['holdings'][0][field]=value
            with self.assertRaises(ValueError):validate(t)
        t=copy.deepcopy(self.initial);t['holdings'][1]['id']=t['holdings'][0]['id']
        with self.assertRaises(ValueError):validate(t)
    def test_missing_and_conflicted_valuation(self):
        t=copy.deepcopy(self.initial);t['holdings'][0]['price']=''
        self.assertEqual(summary(t)['missing'],1)
        t['holdings'][0]['price']='100'
        self.assertEqual(summary(t)['missing'],1)
        t['holdings'][0]['marketValueJpy']=''
        self.assertEqual(summary(t)['rows'][0]['value'],200)
    def test_corruption_detected(self):
        p=self.s.data/'revisions'/self.state['version']/'holdings.csv'
        p.write_text('broken')
        with self.assertRaisesRegex(ValueError,'整合性'):
            self.s.read()
    def test_failed_backup_preserves_pointer(self):
        t=copy.deepcopy(self.initial);t['holdings'][0]['note']='uncommitted'
        self.s.backup_revision=lambda version: (_ for _ in ()).throw(OSError('disk full'))
        with self.assertRaises(OSError):
            self.s.commit(t,self.state['version'],'USER','disk failure')
        self.assertEqual(self.s.read()['version'],self.state['version'])
        self.assertEqual(len(self.s.history()),1)

if __name__=='__main__':
    unittest.main(verbosity=2)

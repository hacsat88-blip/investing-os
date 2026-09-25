"""app/monitor_view.py の受入テスト（標準ライブラリのみ）"""
import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
import monitor_view as mv

NOW = "2026-09-25T12:00:00+09:00"

def run(**kw):
    base = {"schema": "monitor-run-v1", "slot": "0905", "actor": "ai:test", "startedAt": "2026-09-25T09:10:00+09:00",
            "status": "SUCCESS", "alerts": [], "holdings": [], "errors": []}
    base.update(kw); return base

def holding(hid="H1", code="8766", price=None, prev=None, fr="FRESH", cur="JPY"):
    mk = lambda v, t: {"value": v, "asOf": t, "quality": "FACT"} if v is not None else None
    return {"holdingId": hid, "code": code, "name": "N", "currency": cur, "price": mk(*price) if price else None,
            "prevClose": mk(*prev) if prev else None, "freshness": fr, "thesisStatus": None}

class T(unittest.TestCase):
    def render(self, runs, state=None, extra_files=None):
        d = Path(tempfile.mkdtemp()); rd = d / "runs"; rd.mkdir()
        for i, r in enumerate(runs):
            (rd / f"{i}.json").write_text(json.dumps(r), encoding="utf-8")
        for n, t in (extra_files or {}).items():
            (rd / n).write_text(t, encoding="utf-8")
        st = d / "state.json"
        if state is not None:
            st.write_text(json.dumps(state), encoding="utf-8")
        out = d / "dash.html"
        code = mv.main(["--runs-dir", str(rd), "--state", str(st), "--output", str(out), "--now", NOW])
        return code, out.read_text(encoding="utf-8")

    def test_valid_render(self):
        code, h = self.render([run()])
        self.assertEqual(code, 0); self.assertIn("成功", h)

    def test_missing_price_not_zero(self):
        _, h = self.render([run(holdings=[holding()])])
        self.assertIn("取得不可", h); self.assertIn("算出不可", h); self.assertNotIn("0.00%", h)

    def test_change_pct(self):
        _, h = self.render([run(holdings=[holding(price=(110, "2026-09-24T15:30:00+09:00"), prev=(100, "2026-09-22T15:30:00+09:00"))])])
        self.assertIn("+10.00%", h)

    def test_invalid_json_listed_and_exit1(self):
        code, h = self.render([run()], extra_files={"bad.json": "{"})
        self.assertEqual(code, 1); self.assertIn("bad.json", h)

    def test_schema_violations_rejected(self):
        bad = run(status="DONE", startedAt="2026-09-25 09:10")
        code, h = self.render([bad])
        self.assertEqual(code, 1); self.assertIn("statusが不正", h); self.assertIn("startedAt", h)

    def test_zero_or_negative_price_rejected(self):
        code, _ = self.render([run(holdings=[holding(price=(0, "2026-09-24T15:30:00+09:00"))])])
        self.assertEqual(code, 1)

    def test_us_offset_kept_not_shifted(self):
        _, h = self.render([run(slot="0730", holdings=[holding(code="LMT", cur="USD", price=(500.5, "2026-09-24T16:00:00-04:00"))])])
        self.assertIn("09/24 16:00", h); self.assertIn("-04:00", h)

    def test_mixed_dates_flagged(self):
        hs = [holding("H1", price=(1, "2026-09-24T15:30:00+09:00")), holding("H2", code="LMT", cur="USD", price=(2, "2026-09-24T16:00:00-04:00"))]
        _, h = self.render([run(holdings=hs)])
        self.assertIn("基準日が保有ごとに異なります", h)

    def test_unknown_stars_not_one(self):
        a = {"code": "X", "stars": None, "direction": "UNKNOWN", "what": "w"}
        _, h = self.render([run(alerts=[a])])
        self.assertIn("未評価", h); self.assertNotIn('aria-label="星1"', h)

    def test_escape_and_unsafe_link(self):
        a = {"code": "<script>", "stars": 3, "direction": "NEUTRAL", "what": "<b>x</b>", "url": "javascript:alert(1)", "sourceId": "S"}
        _, h = self.render([run(alerts=[a])])
        self.assertNotIn("<script>", h.split("</style>")[1]); self.assertNotIn("javascript:", h)

    def test_failed_run_alerts_excluded(self):
        a = {"code": "X", "stars": 5, "direction": "NEGATIVE", "what": "should-not-show"}
        _, h = self.render([run(status="FAILED", alerts=[a])])
        self.assertNotIn("should-not-show", h)

    def test_star_order(self):
        a1 = {"code": "LOW", "stars": 2, "direction": "NEUTRAL", "what": "low"}
        a2 = {"code": "HIGH", "stars": 5, "direction": "NEGATIVE", "what": "high"}
        _, h = self.render([run(alerts=[a1, a2])])
        self.assertLess(h.index("HIGH"), h.index("LOW"))

    def test_no_external_resources_and_no_amounts(self):
        _, h = self.render([run(holdings=[holding(price=(1, "2026-09-24T15:30:00+09:00"))])])
        self.assertNotRegex(h, r'(src|href)="https?://(?!example)')
        self.assertIn("default-src 'none'", h)
        for k in ("評価額</th>", "数量</th>", "損益</th>"):
            self.assertNotIn(k, h)

    def test_unregistered_slot_shown(self):
        _, h = self.render([], state={"runners": {}})
        self.assertIn("未登録", h); self.assertIn("実行記録なし", h)

if __name__ == "__main__":
    unittest.main()

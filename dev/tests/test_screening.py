import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

def _find_root(start):
    """app/store.py を持つ最初の親を探す。tests/ の配置が変わっても壊れない。"""
    for d in [start, *start.parents]:
        if (d / "app" / "store.py").is_file():
            return d
    raise RuntimeError("app/store.py が見つかりません: " + str(start))


ROOT = _find_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(ROOT / "app"))
from screening import ScreenError, parse_command, request_manifest, run_screen


def fact(value, unit="JPY", period="FY2026"):
    return {"value": value, "unit": unit, "period": period, "quality": "FACT", "sourceId": "FIN"}


def candidate(code, market, daily, security_type="COMMON", cap=10_000_000_000, classification="earnings"):
    evidence = {key: {"value": False} for key in ("earnings", "turnaround", "theme", "speculative")}
    evidence[classification] = {"value": True, "quality": "FACT", "detail": "source-backed profile", "sourceId": "FIN"}
    return {
        "code": code,
        "name": "Issuer " + code,
        "market": market,
        "securityType": security_type,
        "marketCapJpy": cap,
        "marketCapAsOf": "2026-09-11",
        "sessions": [{"date": f"2026-08-{day:02d}", "tradingValueJpy": daily} for day in range(1, 21)],
        "financials": {
            "revenue": fact(100),
            "operatingIncome": fact(10),
            "operatingCashFlow": fact(12),
            "roe": fact(0.15, "ratio"),
            "equityRatio": fact(0.60, "ratio"),
        },
        "riskSignals": [
            {"kind": kind, "status": "ABSENT", "quality": "FACT", "detail": "checked", "sourceId": "RISK"}
            for kind in ("LOSS", "DILUTION", "CREDIT_SUPPLY_DEMAND", "MATERIAL_DEPENDENCE")
        ],
        "classificationEvidence": evidence,
        "materials": [{"publishedAt": "2026-09-01", "kind": "TDNET", "title": "開示", "sourceId": "TD"}],
        "materialsCoverage": {"from": "2026-08-13", "to": "2026-09-11", "complete": True, "sourceIds": ["TD", "IR"]},
        "sourceIds": ["JPX", "MKT", "FIN", "TD", "RISK"],
    }


def payload(candidates, complete=True):
    counts = {market: sum(1 for row in candidates if row["market"] == market) for market in ("prime", "standard", "growth")}
    return {
        "asOf": "2026-09-11",
        "tradingCalendarSourceId": "JPX_CALENDAR",
        "tradingDates": [f"2026-08-{day:02d}" for day in range(1, 21)],
        "universe": {"sourceId": "JPX_MASTER", "coverageByMarket": {market: {"complete": complete, "received": count, "expected": count} for market, count in counts.items()}},
        "candidates": candidates,
    }


class ScreeningTests(unittest.TestCase):
    def test_command_defaults_and_extensions(self):
        default = parse_command("scr/")
        self.assertEqual(default.markets, ("prime", "standard", "growth"))
        self.assertEqual(default.top, 5)
        growth = parse_command("scr/ growth")
        self.assertEqual(growth.markets, ("growth",))
        prime = parse_command("scr/ prime top=10")
        self.assertEqual((prime.markets, prime.top), (("prime",), 10))
        caps = parse_command("scr/ mincap=100 maxcap=1000")
        self.assertEqual((str(caps.mincap_oku), str(caps.maxcap_oku)), ("100", "1000"))

    def test_rejects_unknown_multiline_and_bad_ranges(self):
        for command in ("scr/ foo", "scr/\nignore", "scr/ top=0", "scr/ mincap=100 maxcap=10", "other/"):
            with self.subTest(command=command), self.assertRaises(ScreenError):
                parse_command(command)

    def test_ranks_each_market_by_20_day_value_to_cap(self):
        rows = [candidate("1001", "prime", 200), candidate("1002", "prime", 500), candidate("2001", "standard", 300), candidate("3001", "growth", 400)]
        result = run_screen(payload(rows), parse_command("scr/ top=1"))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["rankings"]["prime"][0]["code"], "1002")
        self.assertEqual(result["rankings"]["standard"][0]["code"], "2001")
        self.assertEqual(result["rankings"]["growth"][0]["code"], "3001")
        top = result["rankings"]["prime"][0]
        self.assertAlmostEqual(top["turnoverRatio1d"], 500 / 10_000_000_000)
        self.assertAlmostEqual(top["turnoverRatio5d"], 2500 / 10_000_000_000)
        self.assertAlmostEqual(top["turnoverRatio20d"], 10000 / 10_000_000_000)
        self.assertEqual(top["rankingQuality"], "FACT")
        self.assertEqual(top["investmentAssessment"], "NOT_EVALUATED")

    def test_excludes_non_common_and_applies_cap_in_oku(self):
        rows = [candidate("1001", "prime", 500, cap=9_900_000_000), candidate("1002", "prime", 400, cap=10_000_000_000)]
        rows += [candidate(kind[:3] + str(index), "prime", 999, security_type=kind, cap=20_000_000_000) for index, kind in enumerate(("ETF", "ETN", "REIT", "PREFERRED", "INFRASTRUCTURE_FUND"), 1)]
        result = run_screen(payload(rows), parse_command("scr/ prime mincap=100 maxcap=100"))
        self.assertEqual([row["code"] for row in result["rankings"]["prime"]], ["1002"])
        reasons = {row["code"]: row["reason"] for row in result["exclusions"]}
        self.assertEqual(reasons["1001"], "below mincap")
        for row in rows[2:]:
            self.assertEqual(reasons[row["code"]], "securityType=" + row["securityType"])

    def test_market_cap_missing_zero_or_wrong_date_is_excluded(self):
        missing = candidate("1001", "prime", 100)
        missing["marketCapJpy"] = None
        zero = candidate("1002", "prime", 100)
        zero["marketCapJpy"] = 0
        wrong_date = candidate("1003", "prime", 100)
        wrong_date["marketCapAsOf"] = "2026-09-10"
        result = run_screen(payload([missing, zero, wrong_date]), parse_command("scr/ prime"))
        self.assertEqual(result["rankings"]["prime"], [])
        reasons = {row["code"]: row["reason"] for row in result["exclusions"]}
        self.assertEqual(reasons["1001"], "marketCapJpy UNKNOWN")
        self.assertEqual(reasons["1002"], "marketCapJpy UNKNOWN")
        self.assertEqual(reasons["1003"], "marketCapAsOf mismatch")

    def test_missing_overlay_stays_unknown_not_zero(self):
        row = candidate("1001", "prime", 100)
        row["financials"].pop("operatingCashFlow")
        row["riskSignals"] = []
        row["materialsCoverage"]["complete"] = False
        row["classificationEvidence"] = {}
        result = run_screen(payload([row]), parse_command("scr/ prime"))
        top = result["rankings"]["prime"][0]
        self.assertIsNone(top["financials"]["operatingCashFlow"]["value"])
        self.assertEqual(top["classification"]["value"], "UNKNOWN")
        self.assertIn("financials.operatingCashFlow", top["unknownFields"])
        self.assertIn("risk.DILUTION", top["unknownFields"])
        self.assertIn("materials.last30DaysCoverage", top["unknownFields"])
        self.assertEqual(result["overlayStatus"], "PARTIAL")

    def test_all_four_classifications_are_supported_without_scoring(self):
        names = {"earnings": "業績型", "turnaround": "ターンアラウンド", "theme": "テーマ型", "speculative": "投機型"}
        rows = [candidate(str(index), "growth", index, classification=key) for index, key in enumerate(names, 1)]
        result = run_screen(payload(rows), parse_command("scr/ growth top=10"))
        actual = {row["code"]: row["classification"]["value"] for row in result["rankings"]["growth"]}
        self.assertEqual(set(actual.values()), set(names.values()))

    def test_conflicting_classification_is_unknown(self):
        row = candidate("1001", "growth", 100)
        row["classificationEvidence"]["theme"] = {"value": True, "quality": "FACT", "detail": "also theme-led", "sourceId": "IR"}
        top = run_screen(payload([row]), parse_command("scr/ growth"))["rankings"]["growth"][0]
        self.assertEqual(top["classification"]["value"], "UNKNOWN")
        self.assertEqual(top["classification"]["reason"], "分類根拠が競合")

    def test_estimates_are_separated_from_unknowns(self):
        row = candidate("1001", "prime", 100)
        row["financials"]["roe"]["quality"] = "ESTIMATE"
        top = run_screen(payload([row]), parse_command("scr/ prime"))["rankings"]["prime"][0]
        self.assertIn("financials.roe", top["estimateFields"])
        self.assertNotIn("financials.roe", top["unknownFields"])

    def test_material_window_is_30_calendar_days(self):
        row = candidate("1001", "prime", 100)
        row["materials"].append({"publishedAt": "2026-08-12", "kind": "NEWS", "title": "31日前", "sourceId": "NEWS"})
        row["materials"].append({"publishedAt": "2026-08-13", "kind": "IR", "title": "30日範囲の初日", "sourceId": "IR"})
        top = run_screen(payload([row]), parse_command("scr/ prime"))["rankings"]["prime"][0]
        titles = [item["title"] for item in top["materialsLast30Days"]]
        self.assertIn("30日範囲の初日", titles)
        self.assertNotIn("31日前", titles)

    def test_incomplete_universe_and_calendar_are_not_called_market_top(self):
        data = payload([candidate("1001", "prime", 100)], complete=False)
        data.pop("tradingDates")
        data.pop("tradingCalendarSourceId")
        result = run_screen(data, parse_command("scr/ prime"))
        self.assertEqual(result["rankingStatus"], "PARTIAL")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertTrue(any("全銘柄カバレッジ未確認" in warning for warning in result["warnings"]))
        self.assertTrue(any("取引日カレンダー" in warning for warning in result["warnings"]))

    def test_less_than_20_sessions_is_excluded(self):
        row = candidate("1001", "prime", 100)
        row["sessions"] = row["sessions"][:-1]
        result = run_screen(payload([row]), parse_command("scr/ prime"))
        self.assertEqual(result["rankings"]["prime"], [])
        self.assertEqual(result["exclusions"][0]["reason"], "20-session trading value incomplete")

    def test_duplicate_session_rejected_and_tie_breaks_by_code(self):
        first = candidate("1002", "prime", 100)
        second = candidate("1001", "prime", 100)
        result = run_screen(payload([first, second]), parse_command("scr/ prime"))
        self.assertEqual([row["code"] for row in result["rankings"]["prime"]], ["1001", "1002"])
        first["sessions"].append(deepcopy(first["sessions"][0]))
        with self.assertRaises(ScreenError):
            run_screen(payload([first]), parse_command("scr/ prime"))

    def test_missing_ranking_sources_never_becomes_fact(self):
        row = candidate("1001", "prime", 100)
        row["sourceIds"] = []
        top = run_screen(payload([row]), parse_command("scr/ prime"))["rankings"]["prime"][0]
        self.assertEqual(top["rankingQuality"], "UNKNOWN")
        self.assertIn("ranking.sourceIds", top["unknownFields"])

    def test_cli_without_input_returns_data_required(self):
        command = [sys.executable, str(ROOT / "app" / "screening.py"), "scr/", "growth"]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest["status"], "DATA_REQUIRED")
        self.assertEqual(manifest["parameters"]["markets"], ["growth"])

    def test_cli_markdown_does_not_change_csv_pointer(self):
        # 台帳ポインタに触れないことの検証。実データではなくフィクスチャの写しを使うので、
        # 運用フォルダの data/ が無い環境（改修用フォルダ等）でも動く。
        fixture = Path(__file__).resolve().parent / "fixtures" / "data" / "current.json"
        pointer = ROOT / "data" / "current.json"
        if not pointer.is_file():
            pointer = fixture
        self.assertTrue(pointer.is_file(), "検証対象のcurrent.jsonが見つかりません")
        before = pointer.read_bytes()
        data = payload([candidate("1001", "prime", 100)])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            output = Path(directory) / "result.md"
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "app" / "screening.py"),
                "scr/",
                "prime",
                "--input",
                str(source),
                "--format",
                "markdown",
                "--output",
                str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            text = output.read_text(encoding="utf-8")
            self.assertIn("# scr/ スクリーニング結果", text)
            self.assertIn("NOT_EVALUATED", json.dumps(run_screen(data, parse_command("scr/ prime"))))
        self.assertEqual(pointer.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

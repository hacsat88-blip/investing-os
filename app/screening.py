"""Deterministic engine for the investingOS ``scr/`` screening command.

The engine never fetches market data.  It validates and ranks an explicitly
provided snapshot so a ChatGPT/Web/MCP collection step can remain separate from
the local CSV ledger and from investment judgement.
"""
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path


MARKETS = ("prime", "standard", "growth")
MARKET_LABELS = {"prime": "プライム", "standard": "スタンダード", "growth": "グロース"}
SECURITY_TYPES = {
    "COMMON",
    "ETF",
    "ETN",
    "REIT",
    "PREFERRED",
    "INFRASTRUCTURE_FUND",
    "OTHER",
}
FINANCIAL_METRICS = ("revenue", "operatingIncome", "operatingCashFlow", "roe", "equityRatio")
RISK_KINDS = ("LOSS", "DILUTION", "CREDIT_SUPPLY_DEMAND", "MATERIAL_DEPENDENCE")
QUALITIES = ("FACT", "ESTIMATE", "UNKNOWN")
CLASSIFICATION_KEYS = {
    "earnings": "業績型",
    "turnaround": "ターンアラウンド",
    "theme": "テーマ型",
    "speculative": "投機型",
}


class ScreenError(ValueError):
    """Raised when command syntax or supplied screening data is unsafe."""


@dataclass(frozen=True)
class ScreenConfig:
    markets: tuple[str, ...] = MARKETS
    top: int = 5
    mincap_oku: Decimal | None = None
    maxcap_oku: Decimal | None = None

    def public(self):
        data = asdict(self)
        data["markets"] = list(self.markets)
        data["mincapOku"] = _json_number(self.mincap_oku)
        data["maxcapOku"] = _json_number(self.maxcap_oku)
        del data["mincap_oku"]
        del data["maxcap_oku"]
        return data


def _decimal(value, label, *, required=True, nonnegative=True):
    if value is None or value == "":
        if required:
            raise ScreenError(label + " がありません")
        return None
    if isinstance(value, bool):
        raise ScreenError(label + " は数値で指定してください")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ScreenError(label + " は数値として読めません") from None
    if not number.is_finite() or (nonnegative and number < 0):
        raise ScreenError(label + " は0以上の有限値にしてください")
    return number


def _json_number(value):
    if value is None:
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _date(value, label):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ScreenError(label + " は YYYY-MM-DD 形式にしてください") from None


def parse_command(text: str) -> ScreenConfig:
    """Parse only the single control line beginning with ``scr/``."""
    if not isinstance(text, str) or not text.strip():
        raise ScreenError("scr/ コマンドがありません")
    if "\n" in text or "\r" in text:
        raise ScreenError("scr/ は入力先頭の1行だけをコマンドとして解釈します")
    try:
        tokens = shlex.split(text.strip())
    except ValueError as exc:
        raise ScreenError("scr/ の構文を解析できません: " + str(exc)) from None
    if not tokens or tokens[0].lower() != "scr/":
        raise ScreenError("コマンドは scr/ で開始してください")
    markets = []
    top = 5
    mincap = maxcap = None
    seen_options = set()
    for token in tokens[1:]:
        low = token.lower()
        if low in MARKETS:
            if markets and low not in markets:
                raise ScreenError("市場は1つだけ指定できます")
            markets = [low]
            continue
        if "=" not in low:
            raise ScreenError("不明な引数です: " + token)
        key, value = low.split("=", 1)
        if key not in ("top", "mincap", "maxcap") or key in seen_options:
            raise ScreenError("不明または重複したオプションです: " + token)
        seen_options.add(key)
        if key == "top":
            if not value.isdigit() or not 1 <= int(value) <= 50:
                raise ScreenError("top は1〜50の整数にしてください")
            top = int(value)
        elif key == "mincap":
            mincap = _decimal(value, "mincap")
        else:
            maxcap = _decimal(value, "maxcap")
    if mincap is not None and maxcap is not None and mincap > maxcap:
        raise ScreenError("mincap は maxcap 以下にしてください")
    return ScreenConfig(tuple(markets or MARKETS), top, mincap, maxcap)


def request_manifest(config: ScreenConfig):
    """Return a data request instead of pretending an external fetch succeeded."""
    return {
        "schemaVersion": "scr-input-v1",
        "status": "DATA_REQUIRED",
        "parameters": config.public(),
        "rankingFormula": "sum(last 20 trading sessions tradingValueJpy) / marketCapJpy",
        "auxiliaryFormula": "sum(last N trading sessions tradingValueJpy) / marketCapJpy; N=1,5,20",
        "marketCapUnitForCommand": "100 million JPY (億円)",
        "requiredSources": [
            "JPX or equivalent current listed-issue master with market and security type",
            "market-data source with 20 trading sessions of per-issue trading value and an as-of market cap",
            "issuer/EDINET financials for revenue, operating income, operating cash flow, ROE and equity ratio",
            "TDnet/issuer IR plus clearly labelled news for the latest 30 calendar days",
            "margin/credit and share-issuance evidence for risk flags",
        ],
        "requiredTopLevelFields": ["asOf", "candidates"],
        "recommendedTopLevelFields": ["tradingDates", "tradingCalendarSourceId", "universe.sourceId", "universe.coverageByMarket", "sources"],
        "note": "The local app has no market-data API. Supply a sourced snapshot; missing data remains UNKNOWN.",
    }


def _normalize_financials(candidate):
    raw = candidate.get("financials") or {}
    result = {}
    unknowns = []
    estimates = []
    for metric in FINANCIAL_METRICS:
        item = raw.get(metric)
        if not isinstance(item, dict) or item.get("value") in (None, ""):
            result[metric] = {"value": None, "unit": None, "period": None, "quality": "UNKNOWN", "sourceId": None}
            unknowns.append("financials." + metric)
            continue
        quality = item.get("quality", "UNKNOWN")
        if quality not in QUALITIES:
            raise ScreenError(candidate["code"] + ": financials." + metric + " の quality が不正です")
        value = _decimal(item.get("value"), candidate["code"] + ": financials." + metric, nonnegative=False)
        result[metric] = {
            "value": _json_number(value),
            "unit": item.get("unit") or None,
            "period": item.get("period") or None,
            "quality": quality,
            "sourceId": item.get("sourceId") or None,
        }
        if quality == "UNKNOWN" or not result[metric]["period"] or not result[metric]["sourceId"]:
            unknowns.append("financials." + metric + " provenance")
        elif quality == "ESTIMATE":
            estimates.append("financials." + metric)
    return result, unknowns, estimates


def _normalize_risks(candidate):
    supplied = candidate.get("riskSignals") or []
    if not isinstance(supplied, list):
        raise ScreenError(candidate["code"] + ": riskSignals は配列にしてください")
    indexed = {}
    for item in supplied:
        if not isinstance(item, dict) or item.get("kind") not in RISK_KINDS:
            raise ScreenError(candidate["code"] + ": リスク種別が不正です")
        kind = item["kind"]
        if kind in indexed:
            raise ScreenError(candidate["code"] + ": 同じリスク種別が重複しています")
        status = item.get("status", "UNKNOWN")
        quality = item.get("quality", "UNKNOWN")
        if status not in ("PRESENT", "ABSENT", "UNKNOWN") or quality not in QUALITIES:
            raise ScreenError(candidate["code"] + ": リスク状態または quality が不正です")
        indexed[kind] = {
            "kind": kind,
            "status": status,
            "quality": quality,
            "detail": item.get("detail") or None,
            "sourceId": item.get("sourceId") or None,
        }
    result = []
    unknowns = []
    estimates = []
    for kind in RISK_KINDS:
        item = indexed.get(kind, {"kind": kind, "status": "UNKNOWN", "quality": "UNKNOWN", "detail": None, "sourceId": None})
        result.append(item)
        if item["status"] == "UNKNOWN" or item["quality"] == "UNKNOWN" or not item["sourceId"]:
            unknowns.append("risk." + kind)
        elif item["quality"] == "ESTIMATE":
            estimates.append("risk." + kind)
    return result, unknowns, estimates


def _classify(candidate):
    evidence = candidate.get("classificationEvidence") or {}
    positives = []
    estimates = []
    for key in CLASSIFICATION_KEYS:
        item = evidence.get(key)
        if not isinstance(item, dict) or item.get("value") is not True:
            continue
        quality = item.get("quality", "UNKNOWN")
        if quality not in QUALITIES:
            raise ScreenError(candidate["code"] + ": classificationEvidence の quality が不正です")
        if quality == "UNKNOWN" or not item.get("sourceId") or not item.get("detail"):
            continue
        positives.append((key, quality, item.get("detail"), item.get("sourceId")))
        if quality == "ESTIMATE":
            estimates.append("classification." + key)
    if len(positives) != 1:
        reason = "分類根拠が不足" if not positives else "分類根拠が競合"
        return {"value": "UNKNOWN", "quality": "UNKNOWN", "reason": reason, "sourceId": None}, ["classification"], estimates
    key, quality, detail, source_id = positives[0]
    return {"value": CLASSIFICATION_KEYS[key], "quality": quality, "reason": detail, "sourceId": source_id}, [], estimates


def _recent_materials(candidate, as_of):
    materials = candidate.get("materials") or []
    if not isinstance(materials, list):
        raise ScreenError(candidate["code"] + ": materials は配列にしてください")
    start = as_of - timedelta(days=29)
    recent = []
    for item in materials:
        if not isinstance(item, dict):
            raise ScreenError(candidate["code"] + ": material の形式が不正です")
        published = _date(item.get("publishedAt"), candidate["code"] + ": material.publishedAt")
        if start <= published <= as_of:
            recent.append({
                "publishedAt": published.isoformat(),
                "kind": item.get("kind") or "UNKNOWN",
                "title": item.get("title") or "（表題不明）",
                "sourceId": item.get("sourceId") or None,
            })
    recent.sort(key=lambda item: (item["publishedAt"], item["title"]), reverse=True)
    coverage = candidate.get("materialsCoverage") or {}
    complete = (
        coverage.get("complete") is True
        and coverage.get("sourceIds")
        and _date(coverage.get("from"), candidate["code"] + ": materialsCoverage.from") <= start
        and _date(coverage.get("to"), candidate["code"] + ": materialsCoverage.to") >= as_of
    ) if coverage else False
    unknowns = [] if complete else ["materials.last30DaysCoverage"]
    if any(not item["sourceId"] for item in recent):
        unknowns.append("materials.sourceId")
    return recent, unknowns


def _coverage_state(payload, markets, candidate_counts):
    universe = payload.get("universe") or {}
    raw = universe.get("coverageByMarket") or {}
    source_id = universe.get("sourceId")
    complete = True
    rows = {}
    warnings = []
    for market in markets:
        item = raw.get(market) or {}
        actual = candidate_counts.get(market, 0)
        claimed = item.get("received")
        expected = item.get("expected")
        ok = bool(source_id) and item.get("complete") is True and claimed == actual and isinstance(expected, int) and expected == actual
        rows[market] = {"complete": ok, "received": actual, "expected": expected}
        if not ok:
            complete = False
            warnings.append(MARKET_LABELS[market] + ": 全銘柄カバレッジ未確認。順位は取得済み範囲内です")
    return ("COMPLETE" if complete else "PARTIAL"), rows, warnings


def run_screen(payload: dict, config: ScreenConfig):
    """Validate a supplied snapshot and rank candidates without investment scoring."""
    if not isinstance(payload, dict):
        raise ScreenError("入力はJSONオブジェクトにしてください")
    as_of = _date(payload.get("asOf"), "asOf")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 10000:
        raise ScreenError("candidates は10000件以下の配列にしてください")
    trading_dates_raw = payload.get("tradingDates")
    calendar_verified = bool(payload.get("tradingCalendarSourceId")) and isinstance(trading_dates_raw, list) and len(trading_dates_raw) >= 20
    expected_dates = []
    if calendar_verified:
        expected_dates = sorted({_date(value, "tradingDates").isoformat() for value in trading_dates_raw if _date(value, "tradingDates") <= as_of})[-20:]
        calendar_verified = len(expected_dates) == 20

    seen = set()
    candidate_counts = {market: 0 for market in MARKETS}
    eligible = {market: [] for market in config.markets}
    exclusions = []
    global_warnings = [] if calendar_verified else ["取引日カレンダーが未確認のため、20行を20営業日とみなした暫定順位です"]
    for raw in candidates:
        if not isinstance(raw, dict):
            raise ScreenError("candidate の形式が不正です")
        code = str(raw.get("code") or "").strip()
        name = str(raw.get("name") or "").strip()
        market = str(raw.get("market") or "").lower()
        security_type = str(raw.get("securityType") or "").upper()
        if not code or not name or market not in MARKETS or security_type not in SECURITY_TYPES:
            raise ScreenError("code/name/market/securityType が不正な候補があります")
        key = (market, code)
        if key in seen:
            raise ScreenError(market + ": " + code + " が重複しています")
        seen.add(key)
        candidate_counts[market] += 1
        if market not in config.markets:
            continue
        if security_type != "COMMON":
            exclusions.append({"code": code, "name": name, "market": market, "reason": "securityType=" + security_type})
            continue
        cap = _decimal(raw.get("marketCapJpy"), code + ": marketCapJpy", required=False)
        if cap is None or cap <= 0:
            exclusions.append({"code": code, "name": name, "market": market, "reason": "marketCapJpy UNKNOWN"})
            continue
        if raw.get("marketCapAsOf") != as_of.isoformat():
            exclusions.append({"code": code, "name": name, "market": market, "reason": "marketCapAsOf mismatch"})
            continue
        cap_oku = cap / Decimal("100000000")
        if config.mincap_oku is not None and cap_oku < config.mincap_oku:
            exclusions.append({"code": code, "name": name, "market": market, "reason": "below mincap"})
            continue
        if config.maxcap_oku is not None and cap_oku > config.maxcap_oku:
            exclusions.append({"code": code, "name": name, "market": market, "reason": "above maxcap"})
            continue
        sessions = raw.get("sessions")
        if not isinstance(sessions, list):
            exclusions.append({"code": code, "name": name, "market": market, "reason": "sessions UNKNOWN"})
            continue
        by_date = {}
        for session in sessions:
            if not isinstance(session, dict):
                raise ScreenError(code + ": session の形式が不正です")
            day = _date(session.get("date"), code + ": session.date")
            if day > as_of:
                continue
            day_text = day.isoformat()
            if day_text in by_date:
                raise ScreenError(code + ": session.date が重複しています")
            by_date[day_text] = _decimal(session.get("tradingValueJpy"), code + ": tradingValueJpy", required=False)
        available_dates = sorted(by_date)
        window_dates = expected_dates if calendar_verified else available_dates[-20:]
        if len(window_dates) != 20 or any(by_date.get(day) is None for day in window_dates):
            exclusions.append({"code": code, "name": name, "market": market, "reason": "20-session trading value incomplete"})
            continue
        values = [by_date[day] for day in window_dates]
        ratios = {days: sum(values[-days:]) / cap for days in (1, 5, 20)}
        financials, unknowns, estimates = _normalize_financials({**raw, "code": code})
        risks, risk_unknowns, risk_estimates = _normalize_risks({**raw, "code": code})
        classification, class_unknowns, class_estimates = _classify({**raw, "code": code})
        materials, material_unknowns = _recent_materials({**raw, "code": code}, as_of)
        unknowns += risk_unknowns + class_unknowns + material_unknowns
        estimates += risk_estimates + class_estimates
        ranking_sources = sorted(set(str(x) for x in raw.get("sourceIds", []) if x))
        if not ranking_sources:
            unknowns.append("ranking.sourceIds")
        eligible[market].append({
            "code": code,
            "name": name,
            "market": market,
            "securityType": security_type,
            "marketCapJpy": _json_number(cap),
            "marketCapOku": _json_number(cap_oku),
            "marketCapAsOf": raw.get("marketCapAsOf") or None,
            "turnoverRatio1d": float(ratios[1]),
            "turnoverRatio5d": float(ratios[5]),
            "turnoverRatio20d": float(ratios[20]),
            "rankingQuality": "FACT" if calendar_verified and ranking_sources else "UNKNOWN",
            "windowFrom": window_dates[0],
            "windowTo": window_dates[-1],
            "financials": financials,
            "riskSignals": risks,
            "materialsLast30Days": materials,
            "classification": classification,
            "investmentAssessment": "NOT_EVALUATED",
            "estimateFields": sorted(set(estimates)),
            "unknownFields": sorted(set(unknowns)),
            "sourceIds": ranking_sources,
        })

    ranking_status, coverage, coverage_warnings = _coverage_state(payload, config.markets, candidate_counts)
    global_warnings += coverage_warnings
    rankings = {}
    overlay_status = "COMPLETE"
    for market in config.markets:
        rows = sorted(eligible[market], key=lambda row: (-row["turnoverRatio20d"], row["code"]))[:config.top]
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
            if row["unknownFields"]:
                overlay_status = "PARTIAL"
        rankings[market] = rows
        if not rows:
            ranking_status = "NO_DATA" if ranking_status == "COMPLETE" else ranking_status
    status = "COMPLETE" if ranking_status == "COMPLETE" and overlay_status == "COMPLETE" and calendar_verified else "PARTIAL"
    return {
        "schemaVersion": "scr-output-v1",
        "status": status,
        "rankingStatus": ranking_status,
        "overlayStatus": overlay_status,
        "asOf": as_of.isoformat(),
        "parameters": config.public(),
        "coverageByMarket": coverage,
        "rankingMetric": "20-session cumulative trading value / as-of market cap",
        "rankings": rankings,
        "exclusions": exclusions,
        "warnings": global_warnings,
        "decisionBoundary": "Ranking is an attention/liquidity signal, not an investment rating. No trade or CSV-ledger update was performed.",
    }


def _metric_text(item):
    if item["value"] is None:
        return "Unknown"
    unit = (" " + item["unit"]) if item.get("unit") else ""
    return f"{item['value']}{unit} ({item['quality']}, {item['period'] or 'period unknown'})"


def render_markdown(result):
    lines = [
        "# scr/ スクリーニング結果",
        "",
        f"状態: {result['status']} / ランキング {result['rankingStatus']} / Overlay {result['overlayStatus']}",
        f"基準日: {result['asOf']}",
        "",
        "ランキング順位と投資評価は別です。本出力は投資評価・売買提案・台帳更新を行いません。",
    ]
    for market, rows in result["rankings"].items():
        lines += ["", "## " + MARKET_LABELS[market], "", "|順位|コード・名称|時価総額(億円)|1日|5日|20日主指標|分類|", "|---:|---|---:|---:|---:|---:|---|"]
        for row in rows:
            lines.append(
                f"|{row['rank']}|{row['code']} {row['name']}|{row['marketCapOku']:.1f}|"
                f"{row['turnoverRatio1d']:.1%}|{row['turnoverRatio5d']:.1%}|{row['turnoverRatio20d']:.1%}|"
                f"{row['classification']['value']} ({row['classification']['quality']})|"
            )
            lines += [
                "",
                f"### {row['code']} {row['name']}",
                "Fact: 主指標 " + f"{row['turnoverRatio20d']:.1%}" + f"、計算期間 {row['windowFrom']}〜{row['windowTo']}。",
                "Financial Overlay: " + "; ".join(metric + "=" + _metric_text(row["financials"][metric]) for metric in FINANCIAL_METRICS),
            ]
            estimates = ", ".join(row["estimateFields"]) or "なし"
            unknowns = ", ".join(row["unknownFields"]) or "なし"
            present = [risk["kind"] for risk in row["riskSignals"] if risk["status"] == "PRESENT"]
            lines += [
                "Estimate: " + estimates,
                "Unknown: " + unknowns,
                "Risk: " + (", ".join(present) if present else "確認済みのPRESENTなし（UNKNOWNは上記参照）"),
                "30日材料: " + (" / ".join(item["publishedAt"] + " " + item["title"] for item in row["materialsLast30Days"]) if row["materialsLast30Days"] else "該当入力なし"),
            ]
    if result["warnings"]:
        lines += ["", "## Unknown / Coverage", ""] + ["- " + warning for warning in result["warnings"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="investingOS scr/ deterministic screening engine")
    parser.add_argument("command", nargs="*", help="scr/ [prime|standard|growth] [top=N] [mincap=億円] [maxcap=億円]")
    parser.add_argument("--input", help="sourced scr-input-v1 JSON")
    parser.add_argument("--output", help="output path; stdout when omitted")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    config = parse_command(" ".join(args.command) if args.command else "scr/")
    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = run_screen(payload, config)
    else:
        result = request_manifest(config)
    content = render_markdown(result) if args.format == "markdown" and args.input else json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()

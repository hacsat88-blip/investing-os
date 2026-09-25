#!/usr/bin/env python3
"""investingOS 監視ダッシュボード生成（monitor-run-v1 → 自己完結HTML）

判断はAI、描画はこのスクリプト。どのAIが監視を実行しても同じ画面になる。
- 読むもの: monitoring/runs/*.json（monitor-run-v1）、monitoring/state.json（任意）
- 書くもの: --output のHTML 1枚だけ（一時ファイル→置換）
- しないこと: ネットワーク取得、CSV台帳の読み書き、通知、欠損の0埋め
"""
from __future__ import annotations
import argparse, html, json, os, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = "monitor-run-v1"
SLOTS = [("0730", "07:30", "米国引け後"), ("0905", "09:05", "寄り付き後"),
         ("1135", "11:35", "前場終了後"), ("1540", "15:40", "大引け後"), ("2200", "22:00", "PTS夜間")]
STATUSES = {"SUCCESS", "PARTIAL", "FAILED", "SKIPPED"}
DIRECTIONS = {"POSITIVE", "NEGATIVE", "MIXED", "NEUTRAL", "UNKNOWN"}
FRESHNESS = {"FRESH", "AGING", "STALE", "NO_QUOTE"}
THESIS = {"SUPPORTED", "WATCH", "CHALLENGED", "UNREVIEWED"}
QUALITY = {"FACT", "EST", "UNKNOWN"}
LABEL = {
    "SUCCESS": "成功", "PARTIAL": "一部取得", "FAILED": "失敗", "SKIPPED": "スキップ",
    "POSITIVE": "好材料", "NEGATIVE": "悪材料", "MIXED": "強弱混在", "NEUTRAL": "中立", "UNKNOWN": "不明",
    "FRESH": "新しい", "AGING": "やや古い", "STALE": "古い", "NO_QUOTE": "相場なし",
    "SUPPORTED": "支持", "WATCH": "注視", "CHALLENGED": "反証あり", "UNREVIEWED": "未確認",
}


def parse_dt(v):
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v)
    except ValueError:
        return None
    return d if d.tzinfo else None  # オフセット無しは受け付けない


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def validate(run):
    """monitor-run-v1 の検査。問題の一覧を返す（空なら合格）。"""
    e = []
    if not isinstance(run, dict):
        return ["JSONの最上位がオブジェクトではない"]
    if run.get("schema") != SCHEMA:
        e.append(f"schemaが{SCHEMA}ではない")
    if run.get("slot") not in {s[0] for s in SLOTS}:
        e.append("slotが不正")
    if run.get("status") not in STATUSES:
        e.append("statusが不正")
    if not parse_dt(run.get("startedAt")):
        e.append("startedAtがオフセット付きISO日時ではない")
    if not isinstance(run.get("actor"), str) or not run["actor"]:
        e.append("actorが無い")
    for i, a in enumerate(run.get("alerts") or []):
        s = a.get("stars")
        if s is not None and s not in (1, 2, 3, 4, 5):
            e.append(f"alerts[{i}].starsは1〜5か空欄")
        if a.get("direction") not in DIRECTIONS:
            e.append(f"alerts[{i}].directionが不正")
        if a.get("publishedAt") is not None and not parse_dt(a.get("publishedAt")):
            e.append(f"alerts[{i}].publishedAtがオフセット付きISO日時ではない")
    for i, h in enumerate(run.get("holdings") or []):
        if not h.get("holdingId"):
            e.append(f"holdings[{i}].holdingIdが無い")
        if h.get("freshness") not in FRESHNESS:
            e.append(f"holdings[{i}].freshnessが不正")
        if h.get("thesisStatus") not in THESIS | {None}:
            e.append(f"holdings[{i}].thesisStatusが不正")
        for k in ("price", "prevClose"):
            p = h.get(k)
            if p is None:
                continue
            if not is_num(p.get("value")) or p["value"] <= 0:
                e.append(f"holdings[{i}].{k}.valueは正の数か、{k}自体を空欄に")
            if not parse_dt(p.get("asOf")):
                e.append(f"holdings[{i}].{k}.asOfがオフセット付きISO日時ではない")
            if p.get("quality") not in QUALITY:
                e.append(f"holdings[{i}].{k}.qualityが不正")
    return e


def load_runs(runs_dir):
    runs, bad = [], []
    for p in sorted(Path(runs_dir).glob("*.json")):
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as ex:
            bad.append((p.name, [f"JSONとして読めない: {ex.__class__.__name__}"]))
            continue
        errs = validate(run)
        if errs:
            bad.append((p.name, errs))
        else:
            run["_file"] = p.name
            run["_start"] = parse_dt(run["startedAt"])
            runs.append(run)
    return runs, bad


def change_pct(h):
    p, c = h.get("price"), h.get("prevClose")
    if not p or not c:
        return None
    if (h.get("currency") or "") and p.get("currency", h.get("currency")) != c.get("currency", h.get("currency")):
        return None
    return round((p["value"] / c["value"] - 1) * 100, 2)


def build_model(runs, state, now, alert_hours=48):
    latest = {}
    for r in runs:
        s = r["slot"]
        if s not in latest or r["_start"] > latest[s]["_start"]:
            latest[s] = r
    alerts, seen = [], set()
    horizon = now - timedelta(hours=alert_hours)
    for r in sorted(runs, key=lambda x: x["_start"], reverse=True):
        if r["status"] not in ("SUCCESS", "PARTIAL") or r["_start"] < horizon:
            continue
        for a in r.get("alerts") or []:
            key = a.get("sourceId") or a.get("url") or (a.get("code"), a.get("what"))
            if key in seen:
                continue
            seen.add(key)
            alerts.append({**a, "_slot": r["slot"]})
    alerts.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    alerts.sort(key=lambda a: -(a.get("stars") or 0))  # 星の降順、同じ星は新しい順
    holdings = {}
    for r in sorted(runs, key=lambda x: x["_start"]):
        if r["status"] not in ("SUCCESS", "PARTIAL"):
            continue
        for h in r.get("holdings") or []:
            holdings[h["holdingId"]] = {**h, "_slot": r["slot"], "_run": r["_start"]}
    dates = {parse_dt(h["price"]["asOf"]).date().isoformat() + "(" + parse_dt(h["price"]["asOf"]).strftime("%z")[:3] + ")"
             for h in holdings.values() if h.get("price")}
    problems = []
    for r in latest.values():
        for er in r.get("errors") or []:
            problems.append((r["slot"], er.get("route", "不明"), er.get("message", "")))
    return {"latest": latest, "alerts": alerts, "holdings": list(holdings.values()),
            "mixed": len(dates) > 1, "dates": sorted(dates), "problems": problems,
            "runners": (state or {}).get("runners") or {}, "sample": any(r.get("sample") for r in runs)}


E = lambda v: html.escape(str(v), quote=True)


def safe_link(url, text):
    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return f'<a href="{E(url)}" rel="noreferrer">{E(text)}</a>'
    return E(text)


def fmt_dt(v):
    d = parse_dt(v)
    if not d:
        return '<span class="unk">時刻不明</span>'
    return f'{d.strftime("%m/%d %H:%M")} <span class="tz">{E(d.strftime("%z")[:3] + ":" + d.strftime("%z")[3:])}</span>'


def render(model, now, ledger_version=None):
    L = model["latest"]
    rail = []
    for slot, t, name in SLOTS:
        r = L.get(slot)
        st = r["status"] if r else "NONE"
        actor = (r or {}).get("actor") or (model["runners"].get(slot) or {}).get("actor") or "未登録"
        when = fmt_dt(r["startedAt"]) if r else '<span class="unk">実行記録なし</span>'
        detail = E(r.get("detail", "")) if r else ""
        rail.append(f'<li class="stop st-{st.lower()}"><span class="dot" aria-hidden="true"></span>'
                    f'<b class="t">{t}</b><span class="n">{name}</span>'
                    f'<span class="s">{LABEL.get(st, "未実行")}</span><span class="w">{when}</span>'
                    f'<span class="a">{E(actor)}</span><span class="d">{detail}</span></li>')
    al = []
    for a in model["alerts"]:
        s = a.get("stars")
        stars = f'<span class="stars" aria-label="星{s}">{"★" * s}<span class="off">{"★" * (5 - s)}</span></span>' if s else '<span class="stars unk">未評価</span>'
        d = a.get("direction", "UNKNOWN")
        al.append(f'<article class="alert s{s or 0}">{stars}<span class="dir d-{d.lower()}">{LABEL[d]}</span>'
                  f'<h3>{E(a.get("code", ""))} {E(a.get("name", ""))}</h3><p>{E(a.get("what", ""))}</p>'
                  f'<p class="meta">公表 {fmt_dt(a.get("publishedAt"))}　確度 {E(a.get("confidence") or "不明")}　'
                  f'出典 {safe_link(a.get("url"), a.get("sourceId") or "リンク")}</p>'
                  + (f'<p class="next">確認すること：{E(a["checkNext"])}</p>' if a.get("checkNext") else "") + '</article>')
    if not al:
        al.append('<p class="empty">直近48時間に記録された材料はありません。取得できなかった経路は下の「取得できなかったもの」を確認してください。</p>')
    rows = []
    for h in sorted(model["holdings"], key=lambda x: (x.get("currency") != "JPY", str(x.get("code")))):
        p = h.get("price")
        price = f'{p["value"]:,.{0 if h.get("currency") == "JPY" else 2}f} <small>{E(h.get("currency", ""))}</small>' if p else '<span class="unk">取得不可</span>'
        q = f'<small class="q">{E(p["quality"])}</small>' if p else ""
        asof = fmt_dt(p["asOf"]) if p else '<span class="unk">—</span>'
        c = change_pct(h)
        chg = f'<span class="{"up" if c > 0 else "down" if c < 0 else ""}">{c:+.2f}%</span>' if c is not None else '<span class="unk">算出不可</span>'
        th = h.get("thesisStatus")
        rows.append(f'<tr><th scope="row">{E(h.get("code", ""))}<span>{E(h.get("name", ""))}</span></th>'
                    f'<td class="num">{price}{q}</td><td>{asof}</td><td class="num">{chg}</td>'
                    f'<td><span class="fr f-{h["freshness"].lower()}">{LABEL[h["freshness"]]}</span></td>'
                    f'<td>{LABEL.get(th, "") if th else "<span class=unk>未登録</span>"}</td></tr>')
    probs = "".join(f'<li><b>{E(s)}</b> {E(r)}：{E(m)}</li>' for s, r, m in model["problems"])
    bad = "".join(f'<li><b>{E(n)}</b>：{E("／".join(es))}</li>' for n, es in model.get("bad", []))
    mixed = (f'<p class="warn">価格の基準日が保有ごとに異なります：{E("、".join(model["dates"]))}。同じ時点の値として比べないでください。</p>'
             if model["mixed"] else "")
    sample = '<p class="sample">ダミーデータによる表示例です。実際の保有・材料ではありません。</p>' if model["sample"] else ""
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>保有監視 {E(now.strftime("%m/%d %H:%M"))}</title><style>{CSS}</style></head><body><main>
<header><h1>保有監視</h1><p>生成 {E(now.strftime("%Y-%m-%d %H:%M"))}{"　台帳版 " + E(ledger_version[:8]) if ledger_version else ""}</p></header>
{sample}
<section aria-labelledby="h-rail"><h2 id="h-rail">各監視枠の直近の実行</h2><ol class="rail">{"".join(rail)}</ol></section>
<section aria-labelledby="h-al"><h2 id="h-al">重要度の高い材料</h2><div class="alerts">{"".join(al)}</div></section>
<section aria-labelledby="h-h"><h2 id="h-h">保有の値動きと鮮度</h2>{mixed}
<div class="scroll"><table><thead><tr><th scope="col">銘柄</th><th scope="col">価格</th><th scope="col">基準時刻</th><th scope="col">前回比</th><th scope="col">鮮度</th><th scope="col">仮説</th></tr></thead>
<tbody>{"".join(rows) or '<tr><td colspan="6" class="empty">保有の記録がまだありません。</td></tr>'}</tbody></table></div>
<p class="note">評価額・数量・損益はこの画面に載せません。アプリの保有画面で確認してください。</p></section>
<section aria-labelledby="h-p"><h2 id="h-p">取得できなかったもの</h2>
<ul class="probs">{probs or "<li>直近の各枠で報告された取得失敗はありません。</li>"}</ul>
{('<h3>読み込めなかったレポート</h3><ul class="probs bad">' + bad + '</ul>') if bad else ''}</section>
</main></body></html>"""


CSS = """
:root{--fog:#EEF1F4;--paper:#FFFFFF;--ink:#1E2A36;--mute:#5E6B79;--line:#D3DAE2;--amber:#B97812;--pine:#2F7D5B;--crimson:#B23A48;--slate:#7A8594;
font-family:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic",system-ui,sans-serif;color:var(--ink);background:var(--fog)}
@media (prefers-color-scheme:dark){:root{--fog:#141B22;--paper:#1C252E;--ink:#E4EAF0;--mute:#9AA6B3;--line:#2E3A46;--amber:#E0A53D;--pine:#5DB38C;--crimson:#E07080;--slate:#8B96A3}}
*{box-sizing:border-box}body{margin:0;background:var(--fog)}main{max-width:1040px;margin:0 auto;padding:24px 20px 48px}
header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px;border-bottom:2px solid var(--ink);padding-bottom:10px}
h1{font-size:1.75rem;margin:0;letter-spacing:.04em}header p{margin:0;color:var(--mute);font-size:.85rem;font-variant-numeric:tabular-nums}
h2{font-size:1.05rem;margin:32px 0 12px}h3{margin:0}
.sample{background:var(--paper);border-left:4px solid var(--amber);padding:8px 12px;margin:16px 0 0;font-size:.9rem}
.rail{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(5,1fr);position:relative}
.rail::before{content:"";position:absolute;top:9px;left:10%;right:10%;height:2px;background:var(--line)}
.stop{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;padding:0 4px;gap:2px;font-size:.8rem}
.dot{width:20px;height:20px;border-radius:50%;background:var(--paper);border:3px solid var(--slate);z-index:1;margin-bottom:6px}
.st-success .dot{background:var(--pine);border-color:var(--pine)}.st-partial .dot{background:var(--paper);border-color:var(--amber);border-width:6px}
.st-failed .dot{background:var(--crimson);border-color:var(--crimson)}.st-skipped .dot{border-style:dashed}
.t{font-size:1.2rem;font-variant-numeric:tabular-nums}.n{color:var(--mute)}.s{font-weight:700}
.st-failed .s{color:var(--crimson)}.st-partial .s{color:var(--amber)}.st-success .s{color:var(--pine)}
.w,.a,.d{color:var(--mute);font-size:.72rem}.d{max-width:18ch}.tz{color:var(--mute);font-size:.8em}
.alerts{display:flex;flex-direction:column;gap:0;background:var(--paper);border:1px solid var(--line)}
.alert{padding:14px 16px;border-top:1px solid var(--line);display:grid;grid-template-columns:auto auto 1fr;gap:4px 12px;align-items:baseline}
.alert:first-child{border-top:0}.alert h3,.alert p{grid-column:1/-1;margin:0}.alert h3{font-size:1rem}
.alert.s5,.alert.s4{border-left:6px solid var(--amber)}
.stars{color:var(--amber);letter-spacing:1px}.stars .off{color:var(--line)}.stars.unk{color:var(--mute);font-size:.8rem}
.dir{font-size:.75rem;padding:1px 8px;border:1px solid currentColor;border-radius:10px}
.d-positive{color:var(--pine)}.d-negative{color:var(--crimson)}.d-mixed{color:var(--amber)}.d-neutral,.d-unknown{color:var(--mute)}
.meta{color:var(--mute);font-size:.8rem}.next{font-size:.85rem}a{color:inherit}
.scroll{overflow-x:auto;background:var(--paper);border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.88rem;min-width:620px}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:baseline}
thead th{font-size:.75rem;color:var(--mute);font-weight:600}tbody th span{display:block;font-weight:400;color:var(--mute);font-size:.78rem}
.num{text-align:right;font-variant-numeric:tabular-nums}.q{margin-left:6px;color:var(--mute)}
.up{color:var(--pine)}.down{color:var(--crimson)}.unk{color:var(--mute);font-style:italic}
.fr{font-size:.78rem}.f-fresh{color:var(--pine)}.f-aging{color:var(--amber)}.f-stale,.f-no_quote{color:var(--crimson);font-weight:700}
.warn{background:var(--paper);border-left:4px solid var(--amber);padding:8px 12px;font-size:.88rem}
.note,.empty{color:var(--mute);font-size:.82rem}.empty{padding:14px 16px;margin:0}
.probs{padding-left:1.2em;font-size:.88rem}section h3{font-size:.95rem;margin:16px 0 6px}.probs.bad{color:var(--crimson)}
a:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
@media (max-width:640px){.rail{grid-template-columns:1fr;gap:10px}.rail::before{display:none}
.stop{flex-direction:row;flex-wrap:wrap;text-align:left;align-items:center;gap:4px 10px;background:var(--paper);padding:8px 10px;border:1px solid var(--line)}
.dot{margin:0}.d{max-width:none;flex-basis:100%}}
"""


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="monitor-run-v1 から監視ダッシュボードHTMLを生成する")
    ap.add_argument("--runs-dir", default="monitoring/runs")
    ap.add_argument("--state", default="monitoring/state.json")
    ap.add_argument("--output", default="monitoring/dashboard.html")
    ap.add_argument("--ledger-version")
    ap.add_argument("--now", help="テスト用。オフセット付きISO日時")
    a = ap.parse_args(argv)
    now = parse_dt(a.now) if a.now else datetime.now().astimezone()
    if now is None:
        print("--now はオフセット付きISO日時で指定", file=sys.stderr); return 2
    runs, bad = load_runs(a.runs_dir)
    state = None
    if Path(a.state).exists():
        try:
            state = json.loads(Path(a.state).read_text(encoding="utf-8"))
        except ValueError:
            bad.append(("state.json", ["JSONとして読めない"]))
    model = build_model(runs, state, now)
    model["bad"] = bad
    write_atomic(a.output, render(model, now, a.ledger_version))
    print(json.dumps({"output": a.output, "runs": len(runs), "rejected": [n for n, _ in bad]}, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

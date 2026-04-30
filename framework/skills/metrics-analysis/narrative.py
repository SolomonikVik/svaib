"""
DRAFT — судьба этого файла под открытым вопросом #1 (narrative.py vs LLM-сборка).
См. ../../methodology/metrics/open-questions.md, вопрос #1.

Сейчас: универсальный narrative composer (Ветка В оркестратора, Шаг 4).
Может стать: общим skill svaib после решения вопроса #1, либо упростится до
classify_direction (если сборку narrative заберёт LLM), либо исчезнет целиком.

До решения — копия живёт здесь, рабочий оригинал — в
framework/_inbox/metrics-scaffold/sandbox/extractors/narrative.py
(пилот Лебедева, smoke-test работает оттуда).

---

Narrative composer: assembles compound-route Branch В Step 4 output from
extractor JSON. Reads _runs/<file>.json and writes a markdown narrative
to _runs/<file>.narrative.md.

Caracas:
  - Что в норме       (план/факт без значимого разрыва или метрика только-факт без явного отклонения)
  - Что в красной зоне (значимый разрыв план/факт, по убыванию)
  - Что не считается  (status missing/div0/error)

Significance threshold: |fact - plan| / |plan| >= 0.10 (10%) — если plan != 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THRESHOLD = 0.10  # 10% разрыв план/факт = «значимый»


def fmt_money(v: float) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}М"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.0f}К"
    return f"{v:.0f}"


def fmt_pct(v: float) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def fmt_value(v: Any, unit: str) -> str:
    if v is None:
        return "—"
    if not isinstance(v, (int, float)):
        return str(v)
    if unit == "fraction":
        return fmt_pct(v)
    if unit == "RUB":
        return f"{fmt_money(v)} ₽"
    if unit == "count":
        return f"{int(v)}"
    return str(v)


def is_fraction(unit: str) -> bool:
    return unit == "fraction"


def get_aggregate_fact_plan(result: dict[str, Any]) -> tuple[Any, Any]:
    """Return (fact, plan) for a metric result, picking the most general aggregate available.
    For fraction-unit metrics, returns the LAST available month value instead of sum
    (percentages aren't summable). Pre-computed `aggregate` field is ignored for fractions."""
    unit = result.get("unit", "")
    aggregate_fn = (lambda values: values[-1]) if is_fraction(unit) else sum

    # For fraction metrics, skip pre-computed aggregate (extractor sums them blindly).
    if "aggregate" in result and not is_fraction(unit):
        return result["aggregate"].get("sum_fact"), result["aggregate"].get("sum_plan")
    if "q1_total" in result:
        f = result["q1_total"].get("fact", {}).get("value")
        p = result["q1_total"].get("plan", {}).get("value")
        return f, p
    if "fact" in result:
        return result["fact"].get("value"), (result.get("plan") or {}).get("value")
    if "per_month" in result:
        pm = result["per_month"]

        # Shape A: per_month = {fact: {month: {value, status}}, plan: {month: ...}}
        if isinstance(pm.get("fact"), dict):
            try:
                fact_values = [v["value"] for v in pm["fact"].values()
                               if v.get("status") == "ok" and isinstance(v.get("value"), (int, float))]
                fs = aggregate_fn(fact_values) if fact_values else None
            except Exception:
                fs = None
            ps = None
            if isinstance(pm.get("plan"), dict) and pm["plan"]:
                try:
                    plan_values = [v["value"] for v in pm["plan"].values()
                                   if v.get("status") == "ok" and isinstance(v.get("value"), (int, float))]
                    ps = aggregate_fn(plan_values) if plan_values else None
                except Exception:
                    ps = None
            return fs, ps

        # Shape B: per_month = {month: {value, status}} — flat values, q1_dashboard kind
        # Detect by checking first value
        first = next(iter(pm.values())) if pm else None
        if isinstance(first, dict) and "value" in first and "fact" not in first:
            try:
                values = [v["value"] for v in pm.values()
                          if v.get("status") == "ok" and isinstance(v.get("value"), (int, float))]
                fs = aggregate_fn(values) if values else None
                return fs, None
            except Exception:
                return None, None

        # Shape C: per_month = {month: {fact: {value, status}, plan: {value, status}}} — churn_ext kind
        try:
            fact_values = [v.get("fact", {}).get("value") for v in pm.values()
                           if v.get("fact", {}).get("status") == "ok" and isinstance(v.get("fact", {}).get("value"), (int, float))]
            plan_values = [v.get("plan", {}).get("value") for v in pm.values()
                           if v.get("plan", {}).get("status") == "ok" and isinstance(v.get("plan", {}).get("value"), (int, float))]
            fs = aggregate_fn(fact_values) if fact_values else None
            ps = aggregate_fn(plan_values) if plan_values else None
            return fs, ps
        except Exception:
            return None, None
    return None, None


def is_bad_for_metric(delta_pct: float, direction: str) -> bool:
    """Direction-aware: is this deviation in a bad direction?
    direction='increase' (higher = better): fact < plan = bad.
    direction='decrease' (lower = better): fact > plan = bad.
    direction='unknown': can't decide → treat any large deviation as bad (legacy)."""
    if direction == "increase":
        return delta_pct < 0
    if direction == "decrease":
        return delta_pct > 0
    return True  # conservative for unknown


def classify(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (bucket, info). bucket ∈ {ok, red, win, ok_no_plan, blocked}."""
    status = result.get("status", "unknown")
    if status in ("missing", "div0") or status.startswith("unsupported") or status.startswith("unknown"):
        return "blocked", {"reason": status, "label": result.get("label"), "metric_id": result.get("metric_id")}

    fact, plan = get_aggregate_fact_plan(result)
    info = {
        "fact": fact,
        "plan": plan,
        "label": result.get("label"),
        "unit": result.get("unit"),
        "domain": result.get("domain"),
        "metric_id": result.get("metric_id"),
        "direction": result.get("direction", "unknown"),
    }

    if fact is None:
        return "blocked", {"reason": "no_fact", "label": result.get("label"), "metric_id": result.get("metric_id")}

    if plan is None or plan == 0:
        info["delta"] = None
        info["delta_pct"] = None
        return "ok_no_plan", info

    delta = fact - plan
    delta_pct = delta / plan if plan != 0 else 0
    info["delta"] = delta
    info["delta_pct"] = delta_pct

    if abs(delta_pct) < THRESHOLD:
        return "ok", info

    if is_bad_for_metric(delta_pct, info["direction"]):
        return "red", info
    return "win", info


def render_metric_line(info: dict[str, Any], with_delta: bool = True) -> str:
    label = info["label"]
    unit = info["unit"]
    fact = info["fact"]
    plan = info["plan"]
    if plan is None:
        return f"- **{label}** — факт {fmt_value(fact, unit)} _(плана нет)_"
    line = f"- **{label}** — факт {fmt_value(fact, unit)}, план {fmt_value(plan, unit)}"
    if with_delta and info.get("delta_pct") is not None:
        sign = "+" if info["delta"] >= 0 else ""
        line += f" → отклонение {sign}{fmt_value(info['delta'], unit)} ({sign}{info['delta_pct']*100:.1f}%)"
    return line


def render_blocked(result: dict[str, Any], reason: str) -> str:
    label = result.get("label", result.get("metric_id"))
    return f"- **{label}** — {reason}"


def assemble(report: dict[str, Any]) -> str:
    period = report.get("period")
    okr = report.get("okr_group")
    src = report.get("source")
    src_ts = report.get("source_mtime")
    ran = report.get("ran_at")
    results = report.get("results", [])

    lines = []
    title = f"# Compound-route ответ: {okr or 'cross-domain'} за {period}"
    lines.append(title)
    lines.append("")
    lines.append(f"_Источник: `{src}` (mtime {src_ts}). Прогон: {ran}._")
    lines.append("")

    buckets: dict[str, list[Any]] = {"red": [], "win": [], "ok": [], "ok_no_plan": [], "blocked": []}
    for r in results:
        bucket, info = classify(r)
        if bucket == "blocked":
            buckets["blocked"].append((info, info.get("reason", "unknown")))
        else:
            buckets[bucket].append(info)

    # sort red and win by abs(delta_pct) desc
    buckets["red"].sort(key=lambda x: abs(x.get("delta_pct") or 0), reverse=True)
    buckets["win"].sort(key=lambda x: abs(x.get("delta_pct") or 0), reverse=True)

    if buckets["red"]:
        lines.append("## В красной зоне")
        lines.append("")
        lines.append("_Отклонение план/факт в плохую сторону больше 10%._")
        lines.append("")
        for info in buckets["red"]:
            lines.append(render_metric_line(info, with_delta=True))
        lines.append("")

    if buckets["win"]:
        lines.append("## Лучше плана")
        lines.append("")
        lines.append("_Отклонение план/факт в нашу пользу больше 10%._")
        lines.append("")
        for info in buckets["win"]:
            lines.append(render_metric_line(info, with_delta=True))
        lines.append("")

    if buckets["ok"] or buckets["ok_no_plan"]:
        lines.append("## В норме")
        lines.append("")
        for info in buckets["ok"]:
            lines.append(render_metric_line(info, with_delta=True))
        for info in buckets["ok_no_plan"]:
            lines.append(render_metric_line(info, with_delta=False))
        lines.append("")

    if buckets["blocked"]:
        lines.append("## Не считается")
        lines.append("")
        for info, reason in buckets["blocked"]:
            lines.append(render_blocked(info, reason))
        lines.append("")

    # short executive summary
    total = len(results)
    red = len(buckets["red"])
    win = len(buckets["win"])
    blocked = len(buckets["blocked"])
    ok = total - red - win - blocked
    summary = f"**Сводка:** {total} метрик · {red} в красной зоне · {win} лучше плана · {ok} в норме · {blocked} не считается"
    lines.insert(2, summary)
    lines.insert(3, "")

    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", required=True, help="extractor JSON path")
    parser.add_argument("--out", required=True, help="narrative markdown path")
    args = parser.parse_args(argv)

    inp = Path(args.inp)
    if not inp.exists():
        print(f"FAIL: input not found: {inp}")
        return 2

    report = json.loads(inp.read_text(encoding="utf-8"))
    md = assemble(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"OK: wrote narrative to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

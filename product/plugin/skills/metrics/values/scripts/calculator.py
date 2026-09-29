#!/usr/bin/env python3
"""calculator.py — производные из прочитанных значений. Считает код, не модель.

Канон вертикали (architecture.md, «Инструменты»): любое число проходит либо через
extractor, либо через calculator. Чтение отдаёт ряды, этот скрипт — производные от них:

    python3 read_metrics.py --book <книга>.xlsx --card <карта>.json --json > values.json
    python3 calculator.py --values values.json [--period 2026-07] [--json]

Что умеет: выполнение плана, отклонение факта от плана, рост к прошлому году,
изменение к предыдущему периоду. Больше ничего — интерпретация не его работа.

Чего не делает никогда:
  * не складывает и не усредняет проценты — процент считается только от абсолютных
    величин, иначе получается число, похожее на правду (на книге клиента такой
    агрегат разошёлся с абсолютным финрезультатом на 15%);
  * не достраивает отсутствующий период и не берёт соседний вместо пропущенного;
  * не сравнивает величины в разных единицах.
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

PERCENT_UNITS = {"%", "percent", "процент", "проценты"}


def is_percent(row):
    return str(row.get("unit") or "").strip().lower() in PERCENT_UNITS


def prev_period(period):
    """Предыдущий период той же гранулярности: 2026-07 → 2026-06."""
    if "-W" in period or "-Q" in period:
        return None
    try:
        y, m = period.split("-")
        y, m = int(y), int(m)
    except ValueError:
        return None
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def year_ago(period):
    try:
        y, m = period.split("-")
        return f"{int(y) - 1}-{m}"
    except ValueError:
        return None


def derive(rows, period=None):
    """Производные по каждой метрике за выбранный период (по умолчанию — последний с фактом)."""
    by_name = {r["metric"]: r for r in rows}
    out = []
    for row in rows:
        if row.get("status") == "refused" or not row.get("values"):
            continue
        if row.get("companion"):
            continue    # ряд «год назад» — опора для роста, а не самостоятельная метрика
        vals = row["values"]
        p = period or max(vals)
        res = {"metric": row["metric"], "unit": row.get("unit"), "period": p, "derived": {}, "notes": []}
        if p not in vals:
            res["notes"].append(f"за {p} значения нет — производные не считаются")
            out.append(res); continue
        fact = vals[p]
        res["fact"] = fact

        plan = (row.get("plan") or {}).get(p)
        if plan == 0:
            res["notes"].append("план равен нулю — выполнение не считается")
        elif plan is not None:
            res["derived"]["выполнение плана, %"] = round(fact / plan * 100, 1)
            res["derived"]["отклонение от плана"] = round(fact - plan, 2)
            res["plan"] = plan

        prev = prev_period(p)
        if prev and prev in vals:
            res["derived"]["изменение к прошлому периоду"] = round(fact - vals[prev], 2)
            if not is_percent(row) and vals[prev]:
                res["derived"]["изменение к прошлому периоду, %"] = round(
                    (fact - vals[prev]) / abs(vals[prev]) * 100, 1)

        # Прошлый год: либо в этом же ряду, либо отдельной метрикой-компаньоном.
        # Компаньон опознаётся по имени: оно должно содержать имя основной метрики
        # («MRR» → «MRR год назад»). Не нашли — говорим об этом вслух: молчаливо
        # пропущенная производная выглядит как «роста нет», а не «не с чем сравнить».
        ya = year_ago(p)
        base = vals.get(ya)
        if base is None:
            for other in by_name.values():
                if other is row or other.get("status") == "refused":
                    continue
                if row["metric"] in other["metric"] and ya in (other.get("values") or {}):
                    base = other["values"][ya]; break
        if is_percent(row):
            pass                                    # у процента роста в процентах не бывает
        elif base in (None, 0):
            res["notes"].append(
                f"рост к прошлому году не посчитан: нет значения за {ya}. "
                f"Нужен ряд прошлого года — в той же метрике или отдельной записью карты "
                f"с year_offset: -1 и именем, содержащим «{row['metric']}»")
        else:
            res["derived"]["рост к прошлому году, %"] = round((fact - base) / abs(base) * 100, 1)
            res["year_ago"] = base

        if is_percent(row):
            res["notes"].append("метрика в процентах: разница показана в пунктах, "
                                "агрегаты и средние по ней не считаются")
        for n in row.get("notes", []):
            res["notes"].append(n)
        out.append(res)
    return out


def render(items):
    lines = []
    for it in items:
        head = f"**{it['metric']}**" + (f" ({it['unit']})" if it.get("unit") else "") + f" — {it['period']}"
        lines.append(head)
        if "fact" in it:
            row = [f"факт {it['fact']}"]
            if "plan" in it: row.append(f"план {it['plan']}")
            if "year_ago" in it: row.append(f"год назад {it['year_ago']}")
            lines.append("  " + " · ".join(row))
        for k, v in it["derived"].items():
            lines.append(f"  {k}: {v}")
        for n in it["notes"]:
            lines.append(f"  — {n}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--values", required=True, help="выход read_metrics.py --json")
    ap.add_argument("--period", help="период, за который считать (YYYY-MM); по умолчанию последний с фактом")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = json.loads(Path(a.values).read_text(encoding="utf-8"))
    items = derive(rows, a.period)
    print(json.dumps(items, ensure_ascii=False, indent=2) if a.json else render(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

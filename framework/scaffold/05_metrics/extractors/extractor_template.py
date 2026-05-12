"""
Template for a per-client metrics extractor.

Copy this file into a client's `metrics/extractors/` folder and rename it, for
example `ssp_main.py`. Fill in SOURCE_FILE, SHEET_NAME, column maps, and
METRIC_REGISTRY after one-time xlsx reconnaissance.

Rules:
- Coordinates are explicit and reviewed. Do not generate them with an LLM at run time.
- Results are written to JSON via --out. Stdout stays short.
- Missing values and formula errors get explicit statuses, never silent zeroes.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILE = ROOT / "source" / "<source-file>.xlsx"
SHEET_NAME = "<sheet-name>"


# Example period map. Replace with the client's actual sheet coordinates.
PERIOD_COLUMNS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
}


# Fill after domain-file design. Each metric_id should also exist in a
# `metrics/<domain>.md` passport.
METRIC_REGISTRY: dict[str, dict[str, Any]] = {
    "metric_example": {
        "domain": "sales",
        "strategy": "single_row",
        "row_fact": 0,
        "row_plan": 1,
        "label": "Example metric",
        "unit": "RUB",
        "direction": "increase",
        "plan_required": True,
    },
}


GROUPS: dict[str, list[str]] = {
    "main": ["metric_example"],
}


EXCEL_ERRORS = {"#DIV/0!", "#REF!", "#VALUE!", "#N/A", "#NAME?", "#NULL!", "#NUM!"}


def is_error(value: Any) -> bool:
    return isinstance(value, str) and value.strip() in EXCEL_ERRORS


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalize_value(value: Any) -> tuple[Any, str]:
    if is_error(value):
        return None, "div0"
    if is_blank(value):
        return None, "missing"
    return value, "ok"


def read_cell(df: pd.DataFrame, row: int, col: int) -> tuple[Any, str]:
    if row >= df.shape[0] or col >= df.shape[1]:
        return None, "out_of_range"
    return normalize_value(df.iat[row, col])


def extract_single_row(df: pd.DataFrame, spec: dict[str, Any], period: str) -> dict[str, Any]:
    if period not in PERIOD_COLUMNS:
        return {"status": "error", "error": f"unknown_period:{period}"}

    col = PERIOD_COLUMNS[period]
    fact, fact_status = read_cell(df, spec["row_fact"], col)

    plan = None
    plan_status = "not_applicable"
    if spec.get("row_plan") is not None:
        plan, plan_status = read_cell(df, spec["row_plan"], col)

    status = "ok"
    if fact_status != "ok":
        status = fact_status
    elif spec.get("plan_required") and plan_status != "ok":
        status = plan_status

    return {
        "status": status,
        "fact": fact,
        "plan": plan,
        "fact_status": fact_status,
        "plan_status": plan_status,
    }


def extract_metric(df: pd.DataFrame, metric_id: str, period: str) -> dict[str, Any]:
    if metric_id not in METRIC_REGISTRY:
        return {"metric_id": metric_id, "status": "error", "error": "unknown_metric"}

    spec = METRIC_REGISTRY[metric_id]
    strategy = spec["strategy"]
    if strategy == "single_row":
        payload = extract_single_row(df, spec, period)
    else:
        payload = {"status": "error", "error": f"unknown_strategy:{strategy}"}

    return {
        "metric_id": metric_id,
        "label": spec.get("label", metric_id),
        "domain": spec.get("domain"),
        "unit": spec.get("unit"),
        "direction": spec.get("direction"),
        "plan_required": spec.get("plan_required", False),
        "period": period,
        **payload,
    }


def parse_metric_ids(metrics: str | None, group: str | None) -> list[str]:
    if metrics:
        return [metric.strip() for metric in metrics.split(",") if metric.strip()]
    if group:
        if group not in GROUPS:
            print(f"FAIL: unknown group: {group}")
            sys.exit(1)
        return GROUPS[group]
    print("FAIL: provide --metrics or --group")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-client metrics extractor template")
    parser.add_argument("--metrics", help="Comma-separated metric IDs")
    parser.add_argument("--group", help="Named metric group from GROUPS")
    parser.add_argument("--period", required=True, help="Period key, e.g. jan/feb/mar")
    parser.add_argument("--out", required=True, type=Path, help="Output JSON path")
    args = parser.parse_args()

    if not SOURCE_FILE.exists():
        print(f"FAIL: source not found: {SOURCE_FILE}")
        sys.exit(1)

    metric_ids = parse_metric_ids(args.metrics, args.group)
    df = pd.read_excel(SOURCE_FILE, sheet_name=SHEET_NAME, header=None)

    results = [extract_metric(df, metric_id, args.period) for metric_id in metric_ids]
    payload = {
        "source": str(SOURCE_FILE),
        "sheet": SHEET_NAME,
        "period": args.period,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metrics": results,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for item in results if item.get("status") == "ok")
    print(f"OK: wrote {len(results)} metrics to {args.out} (ok={ok})")


if __name__ == "__main__":
    main()

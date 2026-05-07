"""
Pipeline entry point: fetch CPI → calculate metrics → build dashboard.

Usage:
    python src/main.py [--no-fetch]

  --no-fetch  Skip the live API fetch and use cached / fallback data.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "src"))

from fetch_cpi import load_cpi
from calculate_metrics import calculate, build_monthly_series, save_outputs
from build_dashboard import build

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main(skip_fetch: bool = False) -> None:
    settings_path = ROOT / "config" / "settings.yml"
    salary_path   = ROOT / "config" / "salary_inputs.csv"
    raw_dir       = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    dashboard_dir = ROOT / "dashboard"

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch CPI data
    log.info("=== Step 1: Load CPI data ===")
    if skip_fetch:
        from fetch_cpi import _FALLBACK_CPI
        import pandas as pd
        df_cpi = pd.DataFrame(list(_FALLBACK_CPI.items()), columns=["period", "cpi"])
        log.info("Using built-in fallback CPI data (--no-fetch).")
    else:
        df_cpi = load_cpi(settings_path, raw_dir)

    log.info("CPI dataset: %d monthly records (%s → %s)",
             len(df_cpi), df_cpi["period"].iloc[0], df_cpi["period"].iloc[-1])

    # 2. Calculate metrics
    log.info("=== Step 2: Calculate metrics ===")
    df_yearly, summary = calculate(salary_path, settings_path, df_cpi)
    df_monthly = build_monthly_series(df_cpi, settings_path, salary_path)
    save_outputs(df_yearly, summary, df_monthly, processed_dir)

    # 3. Build dashboard
    log.info("=== Step 3: Build dashboard ===")
    build(processed_dir, salary_path, dashboard_dir)

    log.info("=== Done. Dashboard: %s/index.html ===", dashboard_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Swiss Salary Tracker pipeline")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip live API fetch; use cached/fallback data")
    args = parser.parse_args()
    main(skip_fetch=args.no_fetch)

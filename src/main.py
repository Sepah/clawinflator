"""
Pipeline entry point.  Builds dashboards for every configured region.

Usage:
    python src/main.py
    python src/main.py --region uk
    python src/main.py --no-fetch       # skip live API calls
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regions import REGIONS
from calculate_metrics import calculate, build_monthly_series, save_outputs
from build_dashboard import build, build_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def run_region(region_code: str, all_regions: list, skip_fetch: bool = False) -> None:
    region = REGIONS[region_code]
    log.info("━━━━━━━━━━━━━━━ Region: %s %s ━━━━━━━━━━━━━━━",
             region["flag"], region["name"])

    raw_dir = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. CPI
    log.info("Step 1 · Load CPI")
    if skip_fetch:
        # Use cached CSV directly
        suffix = "" if region_code == "ch" else f"_{region_code}"
        cache = raw_dir / f"cpi{suffix}_raw.csv"
        if cache.exists():
            import pandas as pd
            df_cpi = pd.read_csv(cache)
        else:
            df_cpi = region["fetcher"]()  # fall through to fetcher; will use built-in fallback
    else:
        df_cpi = region["fetcher"]()
    log.info("CPI dataset: %d records (%s → %s)",
             len(df_cpi), df_cpi["period"].iloc[0], df_cpi["period"].iloc[-1])

    # 2. Calculate
    log.info("Step 2 · Calculate metrics")
    salary_path = ROOT / region["salary_csv"]
    df_yearly, summary = calculate(
        salary_path=salary_path,
        df_cpi=df_cpi,
        base_year=region["base_year"],
        weekly_hours=region["weekly_hours"],
        weeks_per_year=region["weeks_per_year"],
    )
    df_monthly = build_monthly_series(
        df_cpi=df_cpi,
        salary_path=salary_path,
        base_year=region["base_year"],
        weekly_hours=region["weekly_hours"],
        weeks_per_year=region["weeks_per_year"],
    )
    save_outputs(df_yearly, summary, df_monthly, processed_dir, region_code)

    # 3. Build dashboard
    log.info("Step 3 · Build dashboard")
    build(
        summary=summary,
        df_yearly=df_yearly,
        df_monthly=df_monthly,
        region=region,
        all_regions=all_regions,
        output_path=ROOT / region["output_html"],
    )

    # 4. Excel
    cpi_cache = raw_dir / ("cpi_raw.csv" if region_code == "ch" else f"cpi_{region_code}_raw.csv")
    suffix = "" if region_code == "ch" else f"_{region_code}"
    build_excel(
        summary, df_yearly, df_monthly,
        salary_path, cpi_cache,
        processed_dir / f"salary_tracker{suffix}.xlsx",
    )


def main(region_code: str | None = None, skip_fetch: bool = False) -> None:
    all_regions = list(REGIONS.values())
    codes = [region_code] if region_code else list(REGIONS.keys())
    for c in codes:
        if c not in REGIONS:
            log.error("Unknown region: %s", c)
            sys.exit(1)
        run_region(c, all_regions, skip_fetch=skip_fetch)
    log.info("✅ Done. Dashboards: %s",
             ", ".join(REGIONS[c]["output_html"] for c in codes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Salary tracker pipeline")
    parser.add_argument("--region", choices=list(REGIONS.keys()), help="Run only one region")
    parser.add_argument("--no-fetch", action="store_true", help="Skip live API fetch")
    args = parser.parse_args()
    main(region_code=args.region, skip_fetch=args.no_fetch)

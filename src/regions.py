"""
Region configuration: Switzerland and the United Kingdom.

Each entry tells the pipeline how to build that region's page:
    - input file paths
    - working-hour conventions
    - CPI data fetcher
    - branding (flag, currency, theme colour)
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def _ch_fetcher() -> pd.DataFrame:
    from fetch_cpi import load_cpi
    return load_cpi(
        settings_path=ROOT / "config" / "settings.yml",
        raw_dir=ROOT / "data" / "raw",
    )


def _uk_fetcher() -> pd.DataFrame:
    from fetch_cpi_uk import load_cpi_uk
    return load_cpi_uk(raw_dir=ROOT / "data" / "raw")


REGIONS = {
    "ch": {
        "code": "ch",
        "name": "Switzerland",
        "flag": "🇨🇭",
        "currency": "CHF",
        "currency_symbol": "CHF",
        "thousand_sep": "’",          # Swiss apostrophe
        "weekly_hours": 42,
        "weeks_per_year": 52,
        "base_year": 2023,
        "salary_csv": "config/salary_inputs.csv",
        "cpi_source_label": "Eurostat HICP (CH, all items, 2015=100)",
        "fetcher": _ch_fetcher,
        "output_html": "dashboard/index.html",
        "theme_color": "#d12b2b",     # Swiss red
        "salary_note": "Edit config/salary_inputs.csv with your figures.",
    },
    "uk": {
        "code": "uk",
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "currency": "GBP",
        "currency_symbol": "£",
        "thousand_sep": ",",
        "weekly_hours": 37.5,         # standard UK full-time
        "weeks_per_year": 52,
        "base_year": 2023,
        "salary_csv": "config/salary_inputs_uk.csv",
        "cpi_source_label": "ONS CPI All Items (D7BT, 2015=100)",
        "fetcher": _uk_fetcher,
        "output_html": "dashboard/uk.html",
        "theme_color": "#012169",     # UK blue
        "salary_note": (
            "Default figures: £37k (2019) → £62k (2023). "
            "Edit config/salary_inputs_uk.csv with your own figures."
        ),
    },
}

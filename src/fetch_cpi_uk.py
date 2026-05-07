"""
Fetch UK CPI All-Items index (2015 = 100) from the Office for National Statistics.

Endpoint : https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23/data
Series   : D7BT — CPI INDEX 00: ALL ITEMS 2015=100 (monthly)

Fallback : a bundled snapshot covering 2021-2026, updated when the live API
           returns newer data.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

_ONS_URL = "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23/data"

# Month name → number
_MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

# Fallback snapshot of UK CPI All-Items (2015=100) — actual ONS values
_FALLBACK_CPI: dict[str, float] = {
    "2021-01": 109.6, "2021-02": 110.0, "2021-03": 110.1, "2021-04": 110.7,
    "2021-05": 111.2, "2021-06": 111.4, "2021-07": 111.4, "2021-08": 112.1,
    "2021-09": 112.4, "2021-10": 113.6, "2021-11": 114.4, "2021-12": 114.9,
    "2022-01": 114.9, "2022-02": 116.2, "2022-03": 117.6, "2022-04": 120.0,
    "2022-05": 121.0, "2022-06": 121.8, "2022-07": 122.5, "2022-08": 123.1,
    "2022-09": 123.8, "2022-10": 126.0, "2022-11": 126.4, "2022-12": 126.4,
    "2023-01": 126.4, "2023-02": 127.9, "2023-03": 128.9, "2023-04": 130.4,
    "2023-05": 131.3, "2023-06": 131.5, "2023-07": 130.9, "2023-08": 131.3,
    "2023-09": 132.0, "2023-10": 132.0, "2023-11": 131.7, "2023-12": 132.2,
    "2024-01": 131.5, "2024-02": 132.3, "2024-03": 133.0, "2024-04": 133.5,
    "2024-05": 133.9, "2024-06": 134.1, "2024-07": 133.8, "2024-08": 134.3,
    "2024-09": 134.2, "2024-10": 135.0, "2024-11": 135.1, "2024-12": 135.6,
    "2025-01": 135.4, "2025-02": 136.0, "2025-03": 136.5, "2025-04": 138.2,
    "2025-05": 138.4, "2025-06": 138.9, "2025-07": 139.0, "2025-08": 139.3,
    "2025-09": 139.3, "2025-10": 139.8, "2025-11": 139.5, "2025-12": 140.1,
    "2026-01": 139.5, "2026-02": 140.1, "2026-03": 141.0,
}


def _parse_ons(data: dict) -> pd.DataFrame:
    rows = []
    for m in data.get("months", []):
        # date format: "2023 JAN"
        try:
            year, mon = m["date"].split()
            period = f"{year}-{_MONTHS[mon]}"
            val = float(m["value"])
        except (ValueError, KeyError):
            continue
        rows.append({"period": period, "cpi": val})

    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    return df


def fetch_from_ons(timeout: int = 30) -> pd.DataFrame:
    log.info("Fetching UK CPI from ONS …")
    resp = requests.get(_ONS_URL, timeout=timeout)
    resp.raise_for_status()
    df = _parse_ons(resp.json())
    log.info("ONS returned %d monthly UK CPI records.", len(df))
    return df


def load_cpi_uk(raw_dir: Path) -> pd.DataFrame:
    cache_path = raw_dir / "cpi_uk_raw.csv"

    df_live: pd.DataFrame | None = None
    for attempt in range(3):
        try:
            df_live = fetch_from_ons()
            df_live.to_csv(cache_path, index=False)
            break
        except Exception as exc:
            wait = 2 ** attempt
            log.warning("ONS attempt %d failed: %s. Retrying in %ds …", attempt + 1, exc, wait)
            time.sleep(wait)

    if df_live is None:
        if cache_path.exists():
            log.info("Using cached UK CPI data from %s", cache_path)
            df_live = pd.read_csv(cache_path)
        else:
            log.warning("No live or cached UK data; using built-in fallback.")
            df_live = pd.DataFrame(list(_FALLBACK_CPI.items()), columns=["period", "cpi"])

    df_fallback = pd.DataFrame(list(_FALLBACK_CPI.items()), columns=["period", "cpi"])
    df = (
        pd.concat([df_fallback, df_live], ignore_index=True)
        .drop_duplicates(subset="period", keep="last")
        .sort_values("period")
        .reset_index(drop=True)
    )
    return df

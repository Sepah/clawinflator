"""
Fetch Swiss CPI (HICP) data from Eurostat.

Primary source : Eurostat HICP API  — Switzerland (CH), all-items (CP00),
                 base 2015 = 100, monthly
Fallback       : bundled table covering 2021-2025 (actual Eurostat values)

Only ratios between CPI values matter for real-salary calculations, so the
absolute scale (2015 = 100) does not affect results.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests
import yaml

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Eurostat HICP endpoint (Switzerland, all items, 2015=100, monthly)
# ---------------------------------------------------------------------------
_EUROSTAT_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "prc_hicp_midx?geo=CH&coicop=CP00&unit=I15&format=JSON"
)

# ---------------------------------------------------------------------------
# Fallback dataset: actual Eurostat HICP values (2015 = 100)
# ---------------------------------------------------------------------------
_FALLBACK_CPI: dict[str, float] = {
    "2021-01": 100.24, "2021-02": 100.32, "2021-03": 100.53, "2021-04": 100.79,
    "2021-05": 100.99, "2021-06": 101.0,  "2021-07": 101.12, "2021-08": 101.33,
    "2021-09": 101.29, "2021-10": 101.71, "2021-11": 101.57, "2021-12": 101.53,
    "2022-01": 101.69, "2022-02": 102.25, "2022-03": 102.73, "2022-04": 103.15,
    "2022-05": 103.72, "2022-06": 104.27, "2022-07": 104.42, "2022-08": 104.72,
    "2022-09": 104.53, "2022-10": 104.62, "2022-11": 104.49, "2022-12": 104.3,
    "2023-01": 104.99, "2023-02": 105.54, "2023-03": 105.53, "2023-04": 105.8,
    "2023-05": 106.03, "2023-06": 106.1,  "2023-07": 106.58, "2023-08": 106.75,
    "2023-09": 106.57, "2023-10": 106.72, "2023-11": 106.17, "2023-12": 106.44,
    "2024-01": 106.57, "2024-02": 106.8,  "2024-03": 106.74, "2024-04": 107.3,
    "2024-05": 107.58, "2024-06": 107.44, "2024-07": 107.89, "2024-08": 107.86,
    "2024-09": 107.5,  "2024-10": 107.48, "2024-11": 106.92, "2024-12": 106.86,
    "2025-01": 106.8,  "2025-02": 106.95, "2025-03": 106.86, "2025-04": 107.61,
    "2025-05": 107.4,  "2025-06": 107.66, "2025-07": 108.02, "2025-08": 107.91,
    "2025-09": 107.55, "2025-10": 107.55, "2025-11": 106.91, "2025-12": 107.07,
}


# ---------------------------------------------------------------------------
# Eurostat JSON-stat parser
# ---------------------------------------------------------------------------

def _parse_eurostat(data: dict) -> pd.DataFrame:
    """Parse the Eurostat JSON-stat response into a (period, cpi) DataFrame."""
    time_dim = data["dimension"]["time"]
    # index maps position → time label key
    pos_to_key = {v: k for k, v in time_dim["category"]["index"].items()}
    key_to_label = time_dim["category"]["label"]

    records = []
    for idx_str, val in data["value"].items():
        key = pos_to_key[int(idx_str)]
        period = key_to_label[key]
        records.append({"period": period, "cpi": float(val)})

    df = pd.DataFrame(records).sort_values("period").reset_index(drop=True)
    return df


def fetch_from_eurostat(timeout: int = 30) -> pd.DataFrame:
    """Fetch Swiss monthly HICP from Eurostat."""
    log.info("Fetching Swiss HICP from Eurostat …")
    resp = requests.get(_EUROSTAT_URL, timeout=timeout)
    resp.raise_for_status()
    df = _parse_eurostat(resp.json())
    log.info("Eurostat returned %d monthly CPI records.", len(df))
    return df


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def load_cpi(settings_path: Path, raw_dir: Path) -> pd.DataFrame:
    """
    Return a DataFrame with columns [period, cpi] (period = 'YYYY-MM').
    Strategy:
      1. Try live Eurostat API and cache the result.
      2. If the API fails, load the cached CSV from a previous successful run.
      3. If no cache exists, use the hardcoded fallback table.
    The fallback table is always merged in so historical data is always present.
    """
    # settings_path is accepted for interface consistency; currently unused here.
    cache_path = raw_dir / "cpi_raw.csv"

    df_live: pd.DataFrame | None = None
    for attempt in range(3):
        try:
            df_live = fetch_from_eurostat()
            df_live.to_csv(cache_path, index=False)
            break
        except Exception as exc:
            wait = 2 ** attempt
            log.warning(
                "Eurostat fetch attempt %d failed: %s. Retrying in %ds …",
                attempt + 1, exc, wait,
            )
            time.sleep(wait)

    if df_live is None:
        if cache_path.exists():
            log.info("Using cached CPI data from %s", cache_path)
            df_live = pd.read_csv(cache_path)
        else:
            log.warning("No live or cached data; using built-in fallback table.")
            df_live = pd.DataFrame(list(_FALLBACK_CPI.items()), columns=["period", "cpi"])

    # Merge: live data takes priority; fallback fills any missing historical gaps
    df_fallback = pd.DataFrame(list(_FALLBACK_CPI.items()), columns=["period", "cpi"])
    df = (
        pd.concat([df_fallback, df_live], ignore_index=True)
        .drop_duplicates(subset="period", keep="last")
        .sort_values("period")
        .reset_index(drop=True)
    )
    return df

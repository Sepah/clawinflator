"""
Calculate purchasing-power metrics for each salary year and for the latest
available CPI month.

All monetary values are in CHF.
Real values are expressed in base-year (2023) CHF.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _annual_avg_cpi(df_cpi: pd.DataFrame, year: int) -> float | None:
    mask = df_cpi["period"].str.startswith(str(year))
    vals = df_cpi.loc[mask, "cpi"].dropna()
    return float(vals.mean()) if len(vals) > 0 else None


def _latest_cpi(df_cpi: pd.DataFrame) -> tuple[str, float]:
    row = df_cpi.dropna(subset=["cpi"]).iloc[-1]
    return str(row["period"]), float(row["cpi"])


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate(
    salary_path: Path,
    settings_path: Path,
    df_cpi: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Returns
    -------
    df_yearly : DataFrame with one row per salary year
    summary   : dict with latest-period KPIs for the dashboard
    """
    with open(settings_path) as f:
        settings = yaml.safe_load(f)

    base_year: int = int(settings["base_year"])
    annual_hours: int = int(settings["weekly_hours"]) * int(settings["weeks_per_year"])

    df_salary = pd.read_csv(salary_path)

    # Annual average CPI for each salary year
    df_salary["cpi_annual_avg"] = df_salary["year"].apply(
        lambda y: _annual_avg_cpi(df_cpi, y)
    )

    base_cpi = df_salary.loc[df_salary["year"] == base_year, "cpi_annual_avg"].iloc[0]
    if base_cpi is None:
        raise ValueError(f"No CPI data available for base year {base_year}.")
    log.info("Base CPI (%d annual avg): %.2f", base_year, base_cpi)

    base_annual = float(
        df_salary.loc[df_salary["year"] == base_year, "annual_chf"].iloc[0]
    )
    base_monthly = float(
        df_salary.loc[df_salary["year"] == base_year, "monthly_chf"].iloc[0]
    )

    rows = []
    for _, row in df_salary.iterrows():
        year = int(row["year"])
        nom_annual = float(row["annual_chf"])
        nom_monthly = float(row["monthly_chf"])
        cpi_yr = row["cpi_annual_avg"]

        nom_hourly = nom_annual / annual_hours
        nom_annual_increase = nom_annual - base_annual
        nom_pct_vs_base = (nom_annual / base_annual - 1) * 100

        if cpi_yr is None:
            real_annual = real_monthly = real_hourly = None
            real_pct_vs_base = cumulative_inflation = None
        else:
            real_annual = nom_annual * base_cpi / cpi_yr
            real_monthly = nom_monthly * base_cpi / cpi_yr
            real_hourly = real_annual / annual_hours
            real_pct_vs_base = (real_annual / base_annual - 1) * 100
            cumulative_inflation = (cpi_yr / base_cpi - 1) * 100

        rows.append(
            {
                "year": year,
                "nominal_monthly": nom_monthly,
                "nominal_annual": nom_annual,
                "nominal_hourly": nom_hourly,
                "nominal_pct_vs_base": nom_pct_vs_base,
                "cpi_annual_avg": cpi_yr,
                "cumulative_inflation_pct": cumulative_inflation,
                "real_annual": real_annual,
                "real_monthly": real_monthly,
                "real_hourly": real_hourly,
                "real_pct_vs_base": real_pct_vs_base,
                "annual_gain_loss_vs_base": (real_annual - base_annual)
                if real_annual is not None
                else None,
                "monthly_gain_loss_vs_base": (real_monthly - base_monthly)
                if real_monthly is not None
                else None,
            }
        )

    df_yearly = pd.DataFrame(rows)

    # YoY real change
    df_yearly["real_pct_vs_prev_year"] = df_yearly["real_annual"].pct_change() * 100

    # ------------------------------------------------------------------ #
    # Latest-month KPIs (most recent salary year + latest CPI month)
    # ------------------------------------------------------------------ #
    latest_period, latest_cpi_val = _latest_cpi(df_cpi)
    latest_year = int(latest_period[:4])

    # Use the most recent salary year from the table. If CPI hasn't yet caught up
    # (e.g. salary data for 2026 exists but CPI only goes to 2025), we still show
    # the current salary adjusted with the latest available CPI.
    salary_years = sorted(df_salary["year"].tolist())
    current_salary_year = max(salary_years)
    current_row = df_salary[df_salary["year"] == current_salary_year].iloc[0]

    cur_nom_annual = float(current_row["annual_chf"])
    cur_nom_monthly = float(current_row["monthly_chf"])
    cur_real_annual = cur_nom_annual * base_cpi / latest_cpi_val
    cur_real_monthly = cur_nom_monthly * base_cpi / latest_cpi_val
    cur_real_hourly = cur_real_annual / annual_hours

    summary = {
        "latest_cpi_period": latest_period,
        "latest_cpi_value": round(latest_cpi_val, 2),
        "base_cpi": round(base_cpi, 2),
        "base_year": base_year,
        "annual_hours": annual_hours,
        "current_salary_year": current_salary_year,
        "nominal_monthly": round(cur_nom_monthly, 2),
        "nominal_annual": round(cur_nom_annual, 2),
        "nominal_hourly": round(cur_nom_annual / annual_hours, 2),
        "real_monthly": round(cur_real_monthly, 2),
        "real_annual": round(cur_real_annual, 2),
        "real_hourly": round(cur_real_hourly, 2),
        "cumulative_inflation_pct": round((latest_cpi_val / base_cpi - 1) * 100, 2),
        "nominal_increase_vs_base_pct": round(
            (cur_nom_annual / base_annual - 1) * 100, 2
        ),
        "real_increase_vs_base_pct": round(
            (cur_real_annual / base_annual - 1) * 100, 2
        ),
        "annual_gain_loss_vs_base": round(cur_real_annual - base_annual, 2),
        "monthly_gain_loss_vs_base": round(cur_real_monthly - base_monthly, 2),
    }

    return df_yearly, summary


# ---------------------------------------------------------------------------
# Monthly CPI series for the trend chart
# ---------------------------------------------------------------------------

def build_monthly_series(
    df_cpi: pd.DataFrame,
    settings_path: Path,
    salary_path: Path,
) -> pd.DataFrame:
    """Return monthly real-vs-nominal purchasing-power series for charting."""
    with open(settings_path) as f:
        settings = yaml.safe_load(f)

    base_year = int(settings["base_year"])
    annual_hours = int(settings["weekly_hours"]) * int(settings["weeks_per_year"])

    df_salary = pd.read_csv(salary_path).sort_values("year")
    salary_years = sorted(df_salary["year"].tolist())

    # Base CPI: annual average for base year
    base_cpi_vals = df_cpi[df_cpi["period"].str.startswith(str(base_year))]["cpi"].dropna()
    base_cpi = float(base_cpi_vals.mean()) if len(base_cpi_vals) > 0 else None
    if base_cpi is None:
        return pd.DataFrame()

    base_annual = float(df_salary[df_salary["year"] == base_year]["annual_chf"].iloc[0])

    df_monthly = df_cpi[df_cpi["period"] >= f"{base_year}-01"].copy()

    def _salary_for_period(period: str) -> tuple[float, float]:
        yr = int(period[:4])
        sal_yr = max(y for y in salary_years if y <= yr)
        row = df_salary[df_salary["year"] == sal_yr].iloc[0]
        return float(row["annual_chf"]), float(row["monthly_chf"])

    records = []
    for _, row in df_monthly.iterrows():
        if pd.isna(row["cpi"]):
            continue
        nom_annual, nom_monthly = _salary_for_period(row["period"])
        real_annual = nom_annual * base_cpi / row["cpi"]
        records.append(
            {
                "period": row["period"],
                "cpi": row["cpi"],
                "nominal_annual": nom_annual,
                "real_annual": real_annual,
                "nominal_monthly": nom_monthly,
                "real_monthly": nom_monthly * base_cpi / row["cpi"],
                "nominal_hourly": nom_annual / annual_hours,
                "real_hourly": real_annual / annual_hours,
                "cumulative_inflation_pct": (row["cpi"] / base_cpi - 1) * 100,
                "real_gain_loss_annual": real_annual - base_annual,
            }
        )

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Persist outputs
# ---------------------------------------------------------------------------

def save_outputs(
    df_yearly: pd.DataFrame,
    summary: dict,
    df_monthly: pd.DataFrame,
    processed_dir: Path,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)

    df_yearly.to_csv(processed_dir / "salary_metrics_yearly.csv", index=False)
    df_monthly.to_csv(processed_dir / "salary_metrics_monthly.csv", index=False)

    with open(processed_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log.info("Outputs saved to %s", processed_dir)

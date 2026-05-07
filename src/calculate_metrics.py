"""
Calculate purchasing-power metrics for each salary year and the latest CPI month.

Region-agnostic: works for any currency / column convention. The salary CSV
must have columns:  year, monthly_<ccy>, annual_<ccy>  (case-insensitive ccy).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

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


def _detect_columns(df_salary: pd.DataFrame) -> tuple[str, str]:
    """Find the monthly_* and annual_* columns regardless of currency suffix."""
    monthly = next(c for c in df_salary.columns if c.startswith("monthly_"))
    annual  = next(c for c in df_salary.columns if c.startswith("annual_"))
    return monthly, annual


# ---------------------------------------------------------------------------
# Yearly + summary
# ---------------------------------------------------------------------------

def calculate(
    salary_path: Path,
    df_cpi: pd.DataFrame,
    base_year: int,
    weekly_hours: float,
    weeks_per_year: int,
) -> tuple[pd.DataFrame, dict]:
    annual_hours = weekly_hours * weeks_per_year

    df_salary = pd.read_csv(salary_path)
    col_monthly, col_annual = _detect_columns(df_salary)

    df_salary["cpi_annual_avg"] = df_salary["year"].apply(
        lambda y: _annual_avg_cpi(df_cpi, y)
    )

    base_cpi = df_salary.loc[df_salary["year"] == base_year, "cpi_annual_avg"].iloc[0]
    if base_cpi is None:
        raise ValueError(f"No CPI data for base year {base_year}")
    base_annual = float(df_salary.loc[df_salary["year"] == base_year, col_annual].iloc[0])
    base_monthly = float(df_salary.loc[df_salary["year"] == base_year, col_monthly].iloc[0])

    rows = []
    for _, row in df_salary.iterrows():
        year = int(row["year"])
        nom_annual = float(row[col_annual])
        nom_monthly = float(row[col_monthly])
        cpi_yr = row["cpi_annual_avg"]

        nom_hourly = nom_annual / annual_hours
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

        rows.append({
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
            "annual_gain_loss_vs_base": (real_annual - base_annual) if real_annual is not None else None,
            "monthly_gain_loss_vs_base": (real_monthly - base_monthly) if real_monthly is not None else None,
        })

    df_yearly = pd.DataFrame(rows)
    df_yearly["real_pct_vs_prev_year"] = df_yearly["real_annual"].pct_change() * 100

    # Latest snapshot
    latest_period, latest_cpi_val = _latest_cpi(df_cpi)
    salary_years = sorted(df_salary["year"].tolist())
    current_salary_year = max(salary_years)
    cur_row = df_salary[df_salary["year"] == current_salary_year].iloc[0]
    cur_nom_annual = float(cur_row[col_annual])
    cur_nom_monthly = float(cur_row[col_monthly])
    cur_real_annual = cur_nom_annual * base_cpi / latest_cpi_val
    cur_real_monthly = cur_nom_monthly * base_cpi / latest_cpi_val

    summary = {
        "latest_cpi_period": latest_period,
        "latest_cpi_value": round(latest_cpi_val, 2),
        "base_cpi": round(base_cpi, 2),
        "base_year": base_year,
        "annual_hours": annual_hours,
        "weekly_hours": weekly_hours,
        "current_salary_year": current_salary_year,
        "nominal_monthly": round(cur_nom_monthly, 2),
        "nominal_annual": round(cur_nom_annual, 2),
        "nominal_hourly": round(cur_nom_annual / annual_hours, 2),
        "real_monthly": round(cur_real_monthly, 2),
        "real_annual": round(cur_real_annual, 2),
        "real_hourly": round(cur_real_annual / annual_hours, 2),
        "cumulative_inflation_pct": round((latest_cpi_val / base_cpi - 1) * 100, 2),
        "nominal_increase_vs_base_pct": round((cur_nom_annual / base_annual - 1) * 100, 2),
        "real_increase_vs_base_pct": round((cur_real_annual / base_annual - 1) * 100, 2),
        "annual_gain_loss_vs_base": round(cur_real_annual - base_annual, 2),
        "monthly_gain_loss_vs_base": round(cur_real_monthly - base_monthly, 2),
    }

    return df_yearly, summary


# ---------------------------------------------------------------------------
# Monthly series
# ---------------------------------------------------------------------------

def build_monthly_series(
    df_cpi: pd.DataFrame,
    salary_path: Path,
    base_year: int,
    weekly_hours: float,
    weeks_per_year: int,
) -> pd.DataFrame:
    annual_hours = weekly_hours * weeks_per_year
    df_salary = pd.read_csv(salary_path).sort_values("year")
    col_monthly, col_annual = _detect_columns(df_salary)
    salary_years = sorted(df_salary["year"].tolist())

    base_cpi_vals = df_cpi[df_cpi["period"].str.startswith(str(base_year))]["cpi"].dropna()
    if len(base_cpi_vals) == 0:
        return pd.DataFrame()
    base_cpi = float(base_cpi_vals.mean())
    base_annual = float(df_salary[df_salary["year"] == base_year][col_annual].iloc[0])

    df_monthly = df_cpi[df_cpi["period"] >= f"{base_year}-01"].copy()

    def _salary_for(period: str) -> tuple[float, float]:
        yr = int(period[:4])
        sal_yr = max(y for y in salary_years if y <= yr) if any(y <= yr for y in salary_years) else min(salary_years)
        row = df_salary[df_salary["year"] == sal_yr].iloc[0]
        return float(row[col_annual]), float(row[col_monthly])

    records = []
    for _, row in df_monthly.iterrows():
        if pd.isna(row["cpi"]):
            continue
        nom_annual, nom_monthly = _salary_for(row["period"])
        real_annual = nom_annual * base_cpi / row["cpi"]
        records.append({
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
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def save_outputs(
    df_yearly: pd.DataFrame,
    summary: dict,
    df_monthly: pd.DataFrame,
    processed_dir: Path,
    region_code: str = "ch",
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{region_code}" if region_code != "ch" else ""
    df_yearly.to_csv(processed_dir / f"salary_metrics_yearly{suffix}.csv", index=False)
    df_monthly.to_csv(processed_dir / f"salary_metrics_monthly{suffix}.csv", index=False)
    with open(processed_dir / f"summary{suffix}.json", "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Outputs saved to %s (region=%s)", processed_dir, region_code)

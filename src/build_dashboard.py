"""
Generate the static HTML dashboard (dashboard/index.html) and the Excel
workbook (data/processed/salary_tracker.xlsx).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _chf(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "N/A"
    s = f"{abs(value):,.{decimals}f}".replace(",", "’")  # Swiss thousand separator
    sign = "-" if value < 0 else ""
    return f"{sign}CHF {s}"


def _pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def _color(value: float | None) -> str:
    if value is None:
        return "#6b7280"
    return "#16a34a" if value >= 0 else "#dc2626"


# ---------------------------------------------------------------------------
# Build chart data payloads (Plotly traces)
# ---------------------------------------------------------------------------

def _chart_yearly(df: pd.DataFrame) -> str:
    years = df["year"].tolist()
    nom = [round(v, 0) if pd.notna(v) else None for v in df["nominal_annual"]]
    real = [round(v, 0) if pd.notna(v) else None for v in df["real_annual"]]

    traces = [
        {
            "x": years, "y": nom, "name": "Nominal salary",
            "type": "bar", "marker": {"color": "#3b82f6"},
        },
        {
            "x": years, "y": real, "name": "Real salary (2023 CHF)",
            "type": "bar", "marker": {"color": "#22c55e"},
        },
    ]
    layout = {
        "title": "Annual salary: nominal vs real",
        "barmode": "group",
        "yaxis": {"title": "CHF", "tickformat": ",.0f"},
        "xaxis": {"title": "Year", "type": "category"},
        "legend": {"orientation": "h", "y": -0.2},
        "margin": {"t": 50, "b": 60},
    }
    return json.dumps({"traces": traces, "layout": layout})


def _chart_hourly(df: pd.DataFrame) -> str:
    years = df["year"].tolist()
    nom = [round(v, 2) if pd.notna(v) else None for v in df["nominal_hourly"]]
    real = [round(v, 2) if pd.notna(v) else None for v in df["real_hourly"]]

    traces = [
        {"x": years, "y": nom, "name": "Nominal hourly rate",
         "type": "scatter", "mode": "lines+markers", "line": {"color": "#3b82f6", "width": 2}},
        {"x": years, "y": real, "name": "Real hourly rate (2023 CHF)",
         "type": "scatter", "mode": "lines+markers", "line": {"color": "#22c55e", "width": 2}},
    ]
    layout = {
        "title": "Hourly rate: nominal vs real",
        "yaxis": {"title": "CHF/hour", "tickformat": ",.2f"},
        "xaxis": {"title": "Year", "type": "category"},
        "legend": {"orientation": "h", "y": -0.2},
        "margin": {"t": 50, "b": 60},
    }
    return json.dumps({"traces": traces, "layout": layout})


def _chart_inflation(df_monthly: pd.DataFrame) -> str:
    periods = df_monthly["period"].tolist()
    vals = [round(v, 2) for v in df_monthly["cumulative_inflation_pct"]]

    traces = [
        {"x": periods, "y": vals, "name": "Cumulative inflation since 2023",
         "type": "scatter", "mode": "lines", "fill": "tozeroy",
         "line": {"color": "#f59e0b", "width": 2},
         "fillcolor": "rgba(245,158,11,0.15)"},
    ]
    layout = {
        "title": "Cumulative CPI inflation since 2023 (%)",
        "yaxis": {"title": "% vs 2023 average", "ticksuffix": "%"},
        "xaxis": {"title": "Month"},
        "margin": {"t": 50, "b": 60},
        "shapes": [{"type": "line", "x0": periods[0], "x1": periods[-1],
                    "y0": 0, "y1": 0, "line": {"dash": "dot", "color": "#6b7280"}}],
    }
    return json.dumps({"traces": traces, "layout": layout})


def _chart_real_gain(df_monthly: pd.DataFrame) -> str:
    periods = df_monthly["period"].tolist()
    vals = [round(v, 0) for v in df_monthly["real_gain_loss_annual"]]
    colors = ["#16a34a" if v >= 0 else "#dc2626" for v in vals]

    traces = [
        {"x": periods, "y": vals, "name": "Annual gain/loss vs 2023 baseline",
         "type": "bar", "marker": {"color": colors}},
    ]
    layout = {
        "title": "Real annual purchasing-power gain/loss vs 2023 (CHF)",
        "yaxis": {"title": "CHF", "tickformat": ",.0f"},
        "xaxis": {"title": "Month"},
        "margin": {"t": 50, "b": 60},
        "shapes": [{"type": "line", "x0": periods[0], "x1": periods[-1],
                    "y0": 0, "y1": 0, "line": {"dash": "dot", "color": "#6b7280"}}],
    }
    return json.dumps({"traces": traces, "layout": layout})


# ---------------------------------------------------------------------------
# Yearly summary table rows
# ---------------------------------------------------------------------------

def _table_rows(df: pd.DataFrame) -> str:
    rows_html = []
    for _, r in df.iterrows():
        year = int(r["year"])
        gl_cls = "positive" if (r["annual_gain_loss_vs_base"] or 0) >= 0 else "negative"
        rows_html.append(f"""
        <tr>
          <td class="fw-bold">{year}</td>
          <td>{_chf(r['nominal_monthly'])}</td>
          <td>{_chf(r['nominal_annual'])}</td>
          <td>{_pct(r['nominal_pct_vs_base'])}</td>
          <td>{_pct(r['cumulative_inflation_pct'])}</td>
          <td>{_chf(r['real_monthly'])}</td>
          <td>{_chf(r['real_annual'])}</td>
          <td class="{gl_cls}">{_chf(r['annual_gain_loss_vs_base'])}</td>
          <td class="{gl_cls}">{_pct(r['real_pct_vs_base'])}</td>
          <td>{_chf(r['nominal_hourly'], 2)}</td>
          <td>{_chf(r['real_hourly'], 2)}</td>
        </tr>""")
    return "\n".join(rows_html)


# ---------------------------------------------------------------------------
# Main HTML generation
# ---------------------------------------------------------------------------

def build_html(
    summary: dict,
    df_yearly: pd.DataFrame,
    df_monthly: pd.DataFrame,
) -> str:
    generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    latest_period = summary["latest_cpi_period"]
    base_year = summary["base_year"]

    nom_gain_cls = "positive" if summary["nominal_increase_vs_base_pct"] >= 0 else "negative"
    real_gain_cls = "positive" if summary["real_increase_vs_base_pct"] >= 0 else "negative"
    gl_annual_cls = "positive" if summary["annual_gain_loss_vs_base"] >= 0 else "negative"
    gl_monthly_cls = "positive" if summary["monthly_gain_loss_vs_base"] >= 0 else "negative"

    chart_yearly_json = _chart_yearly(df_yearly)
    chart_hourly_json = _chart_hourly(df_yearly)
    chart_inflation_json = _chart_inflation(df_monthly) if not df_monthly.empty else "null"
    chart_gain_json = _chart_real_gain(df_monthly) if not df_monthly.empty else "null"
    table_rows = _table_rows(df_yearly)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Swiss Salary Tracker</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
  <style>
    :root {{
      --bg: #f1f5f9;
      --card: #ffffff;
      --primary: #1e3a5f;
      --accent: #3b82f6;
      --positive: #16a34a;
      --negative: #dc2626;
      --muted: #64748b;
      --border: #e2e8f0;
      --red: #d12b2b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: #0f172a;
      font-size: 15px;
      line-height: 1.5;
    }}
    header {{
      background: var(--primary);
      color: white;
      padding: 1.25rem 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .header-flag {{ font-size: 1.5rem; }}
    header h1 {{ font-size: 1.25rem; font-weight: 700; letter-spacing: -0.01em; }}
    header p {{ font-size: 0.8rem; opacity: 0.75; margin-top: 2px; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; }}

    /* KPI cards */
    .section-title {{
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin: 1.5rem 0 0.75rem;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 0.75rem;
    }}
    .kpi-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
    }}
    .kpi-label {{
      font-size: 0.72rem;
      font-weight: 500;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 0.35rem;
    }}
    .kpi-value {{
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--primary);
      word-break: break-word;
    }}
    .kpi-sub {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.2rem;
    }}
    .positive {{ color: var(--positive) !important; }}
    .negative {{ color: var(--negative) !important; }}
    .kpi-value.positive {{ color: var(--positive); }}
    .kpi-value.negative {{ color: var(--negative); }}

    /* Charts */
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
      gap: 1rem;
    }}
    .chart-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
    }}
    .chart-card .plotly-graph-div {{ width: 100% !important; }}

    /* Table */
    .table-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      margin-top: 1rem;
    }}
    .table-scroll {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}
    thead {{ background: var(--primary); color: white; }}
    th {{
      padding: 0.65rem 0.75rem;
      text-align: right;
      font-weight: 600;
      white-space: nowrap;
      font-size: 0.72rem;
      letter-spacing: 0.02em;
    }}
    th:first-child {{ text-align: left; }}
    td {{
      padding: 0.55rem 0.75rem;
      text-align: right;
      border-top: 1px solid var(--border);
      white-space: nowrap;
    }}
    td:first-child {{ text-align: left; }}
    tbody tr:hover {{ background: #f8fafc; }}
    .fw-bold {{ font-weight: 600; }}

    /* Explanation box */
    .explainer {{
      background: #eff6ff;
      border-left: 3px solid var(--accent);
      border-radius: 6px;
      padding: 0.9rem 1rem;
      font-size: 0.82rem;
      color: #1e40af;
      margin-top: 1rem;
      line-height: 1.6;
    }}

    /* Footer */
    footer {{
      text-align: center;
      padding: 1.5rem;
      font-size: 0.75rem;
      color: var(--muted);
    }}

    @media (max-width: 600px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .chart-grid {{ grid-template-columns: 1fr; }}
      .kpi-value {{ font-size: 1.1rem; }}
      header h1 {{ font-size: 1.05rem; }}
    }}
  </style>
</head>
<body>

<header>
  <span class="header-flag">🇨🇭</span>
  <div>
    <h1>Swiss Salary Purchasing-Power Tracker</h1>
    <p>Real salary in {base_year} CHF &mdash; updated monthly from Swiss Federal Statistical Office CPI data</p>
  </div>
</header>

<div class="container">

  <!-- ── Current salary ─────────────────────────────── -->
  <div class="section-title">Current salary &mdash; {summary['current_salary_year']}</div>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Nominal monthly</div>
      <div class="kpi-value">{_chf(summary['nominal_monthly'])}</div>
      <div class="kpi-sub">Gross contractual</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Nominal annual</div>
      <div class="kpi-value">{_chf(summary['nominal_annual'])}</div>
      <div class="kpi-sub">13 months equivalent</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Nominal hourly</div>
      <div class="kpi-value">{_chf(summary['nominal_hourly'], 2)}</div>
      <div class="kpi-sub">42 h/week · 2,184 h/year</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Nominal vs {base_year}</div>
      <div class="kpi-value {nom_gain_cls}">{_pct(summary['nominal_increase_vs_base_pct'])}</div>
      <div class="kpi-sub">Before inflation</div>
    </div>
  </div>

  <!-- ── Real purchasing power ──────────────────────── -->
  <div class="section-title">Real purchasing power in {base_year} CHF &mdash; CPI through {latest_period}</div>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Real monthly</div>
      <div class="kpi-value">{_chf(summary['real_monthly'])}</div>
      <div class="kpi-sub">In {base_year} purchasing power</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Real annual</div>
      <div class="kpi-value">{_chf(summary['real_annual'])}</div>
      <div class="kpi-sub">In {base_year} purchasing power</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Real hourly</div>
      <div class="kpi-value">{_chf(summary['real_hourly'], 2)}</div>
      <div class="kpi-sub">In {base_year} CHF</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Real vs {base_year}</div>
      <div class="kpi-value {real_gain_cls}">{_pct(summary['real_increase_vs_base_pct'])}</div>
      <div class="kpi-sub">After inflation</div>
    </div>
  </div>

  <!-- ── Inflation & gain/loss ──────────────────────── -->
  <div class="section-title">Inflation &amp; purchasing-power gain / loss</div>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Cumulative CPI inflation</div>
      <div class="kpi-value" style="color: var(--red)">{_pct(summary['cumulative_inflation_pct'])}</div>
      <div class="kpi-sub">Since {base_year} annual avg (Swiss LIK)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Annual gain/loss vs {base_year}</div>
      <div class="kpi-value {gl_annual_cls}">{_chf(summary['annual_gain_loss_vs_base'])}</div>
      <div class="kpi-sub">Real CHF per year</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Monthly gain/loss vs {base_year}</div>
      <div class="kpi-value {gl_monthly_cls}">{_chf(summary['monthly_gain_loss_vs_base'])}</div>
      <div class="kpi-sub">Real CHF per month</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Latest CPI</div>
      <div class="kpi-value">{summary['latest_cpi_value']}</div>
      <div class="kpi-sub">Swiss LIK (base Dec 2020 = 100) &mdash; {latest_period}</div>
    </div>
  </div>

  <div class="explainer">
    <strong>What is &ldquo;real salary&rdquo;?</strong> &mdash;
    Real salary adjusts your nominal (contractual) salary for inflation, expressing it in
    {base_year} purchasing power using the Swiss Consumer Price Index (LIK/IPC) published by the
    Federal Statistical Office (BFS/OFS). A real increase means your salary bought
    <em>more</em> goods and services than in {base_year}; a real decrease means the opposite.
    Formula: Real&nbsp;salary = Nominal&nbsp;salary &times; CPI<sub>{base_year}</sub> / CPI<sub>current</sub>
  </div>

  <!-- ── Charts ─────────────────────────────────────── -->
  <div class="section-title">Charts</div>
  <div class="chart-grid">
    <div class="chart-card"><div id="chart-yearly"></div></div>
    <div class="chart-card"><div id="chart-hourly"></div></div>
    <div class="chart-card"><div id="chart-inflation"></div></div>
    <div class="chart-card"><div id="chart-gain"></div></div>
  </div>

  <!-- ── Yearly summary table ───────────────────────── -->
  <div class="section-title">Year-by-year detail</div>
  <div class="table-card">
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Year</th>
            <th>Nom. Monthly</th>
            <th>Nom. Annual</th>
            <th>Nom. vs {base_year}</th>
            <th>CPI inflation</th>
            <th>Real Monthly</th>
            <th>Real Annual</th>
            <th>Annual G/L</th>
            <th>Real vs {base_year}</th>
            <th>Nom. Hourly</th>
            <th>Real Hourly</th>
          </tr>
        </thead>
        <tbody>
{table_rows}
        </tbody>
      </table>
    </div>
  </div>

</div><!-- /container -->

<footer>
  Data: Swiss Federal Statistical Office (BFS/OFS) &mdash; LIK (Landesindex der Konsumentenpreise).
  Dashboard generated on {generated}.
  Salary data: contractual gross, 42&nbsp;h/week, 2&thinsp;184&nbsp;h/year.
</footer>

<script>
  var CFG = {{responsive: true, displayModeBar: false}};

  function renderChart(id, payload) {{
    if (!payload) return;
    Plotly.newPlot(id, payload.traces, Object.assign({{
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: {{family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", size: 12}},
    }}, payload.layout), CFG);
  }}

  renderChart("chart-yearly",    {chart_yearly_json});
  renderChart("chart-hourly",    {chart_hourly_json});
  renderChart("chart-inflation", {chart_inflation_json});
  renderChart("chart-gain",      {chart_gain_json});
</script>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# Excel workbook
# ---------------------------------------------------------------------------

def build_excel(
    summary: dict,
    df_yearly: pd.DataFrame,
    df_monthly: pd.DataFrame,
    salary_path: Path,
    cpi_path: Path,
    output_path: Path,
) -> None:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils.dataframe import dataframe_to_rows
    except ImportError:
        log.warning("openpyxl not installed; skipping Excel output.")
        return

    wb = openpyxl.Workbook()

    # --- Sheet 1: Salary_Input ---
    ws1 = wb.active
    ws1.title = "Salary_Input"
    df_sal = pd.read_csv(salary_path)
    for r in dataframe_to_rows(df_sal, index=False, header=True):
        ws1.append(r)

    # --- Sheet 2: CPI_Data ---
    ws2 = wb.create_sheet("CPI_Data")
    if cpi_path.exists():
        df_cpi_raw = pd.read_csv(cpi_path)
        for r in dataframe_to_rows(df_cpi_raw, index=False, header=True):
            ws2.append(r)

    # --- Sheet 3: Calculations ---
    ws3 = wb.create_sheet("Calculations")
    for r in dataframe_to_rows(df_yearly.round(2), index=False, header=True):
        ws3.append(r)

    # --- Sheet 4: Summary ---
    ws4 = wb.create_sheet("Summary")
    ws4.append(["Metric", "Value"])
    for k, v in summary.items():
        ws4.append([k, v])

    wb.save(output_path)
    log.info("Excel workbook saved to %s", output_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(
    processed_dir: Path,
    salary_path: Path,
    dashboard_dir: Path,
) -> None:
    summary_path = processed_dir / "summary.json"
    yearly_path = processed_dir / "salary_metrics_yearly.csv"
    monthly_path = processed_dir / "salary_metrics_monthly.csv"
    cpi_raw_path = processed_dir.parent / "raw" / "cpi_raw.csv"

    with open(summary_path) as f:
        summary = json.load(f)
    df_yearly = pd.read_csv(yearly_path)
    df_monthly = pd.read_csv(monthly_path) if monthly_path.exists() else pd.DataFrame()

    dashboard_dir.mkdir(parents=True, exist_ok=True)

    html = build_html(summary, df_yearly, df_monthly)
    out_html = dashboard_dir / "index.html"
    out_html.write_text(html, encoding="utf-8")
    log.info("Dashboard written to %s", out_html)

    build_excel(
        summary, df_yearly, df_monthly,
        salary_path, cpi_raw_path,
        processed_dir / "salary_tracker.xlsx",
    )

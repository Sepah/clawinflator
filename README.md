# Swiss Salary Purchasing-Power Tracker

An automated tracker that adjusts a Swiss gross salary for CPI inflation and
publishes a mobile-friendly dashboard via GitHub Pages — updated monthly by a
GitHub Actions workflow.

**Live dashboard →** `https://<your-username>.github.io/clawinflator/`

---

## What it shows

| Metric | Description |
|--------|-------------|
| Nominal salary | Contractual gross salary (monthly / annual / hourly) |
| Real salary | Nominal salary expressed in base-year (2023) purchasing power |
| Cumulative CPI inflation | % price-level change since 2023 |
| Nominal vs 2023 | % raise before adjusting for inflation |
| Real vs 2023 | % raise after adjusting for inflation |
| Annual gain / loss | CHF difference in real purchasing power vs 2023 |

**Formula:** `Real salary = Nominal salary × CPI_2023 / CPI_current`

Annual hours = 42 h/week × 52 weeks = **2,184 h/year**

---

## Data sources

| Data | Source |
|------|--------|
| CPI (monthly) | [Eurostat HICP](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_midx/) — Switzerland (CH), all items (CP00), base 2015 = 100 |
| Salary inputs | `config/salary_inputs.csv` (edit to match your situation) |

> **Why Eurostat HICP?** It provides a freely accessible REST API with no
> authentication required. Only CPI *ratios* matter for real-salary
> calculations, so the absolute base (2015 = 100) does not affect the results.

---

## Repo structure

```
clawinflator/
├── config/
│   ├── salary_inputs.csv      # Edit this with your salary data
│   └── settings.yml           # Base year, hours, data source settings
├── data/
│   ├── raw/                   # cpi_raw.csv cached from Eurostat API
│   └── processed/             # salary_metrics_yearly/monthly CSV + summary JSON + Excel
├── src/
│   ├── fetch_cpi.py           # Fetch CPI from Eurostat (with fallback)
│   ├── calculate_metrics.py   # Real-salary calculations
│   ├── build_dashboard.py     # Generate dashboard/index.html + Excel workbook
│   └── main.py                # Pipeline entry point
├── dashboard/
│   └── index.html             # Generated static dashboard (served via GitHub Pages)
├── .github/workflows/
│   └── monthly-update.yml     # GitHub Actions: fetch → calculate → build → deploy
└── requirements.txt
```

---

## Running locally

```bash
# 1. Clone the repo
git clone https://github.com/<you>/clawinflator.git
cd clawinflator

# 2. Create a virtual environment (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the full pipeline
python src/main.py

# Open dashboard/index.html in your browser
```

To skip the live API fetch and use cached / fallback data:

```bash
python src/main.py --no-fetch
```

---

## Updating salary data

Edit **`config/salary_inputs.csv`**:

```csv
year,monthly_chf,annual_chf
2023,7300,94900
2024,7450,96850
2025,7600,98800
2026,8100,105300
```

Then re-run `python src/main.py`.

---

## Enabling GitHub Pages

1. Go to your repository → **Settings → Pages**.
2. Under *Source*, select **GitHub Actions**.
3. The `monthly-update.yml` workflow deploys `dashboard/index.html` on every
   run. Trigger it manually the first time via
   **Actions → Monthly salary tracker update → Run workflow**.

---

## Automated monthly updates

The workflow (`.github/workflows/monthly-update.yml`) runs automatically on
the **5th of every month at 06:00 UTC** — shortly after the Swiss FSO
typically publishes the previous month's CPI.

It also runs on `workflow_dispatch` so you can trigger it manually at any time.

Each run:
1. Fetches the latest Eurostat HICP data
2. Recalculates all metrics
3. Rebuilds `dashboard/index.html`
4. Commits updated files back to the repository
5. Deploys the dashboard to GitHub Pages

---

## Customising

| File | What to change |
|------|----------------|
| `config/salary_inputs.csv` | Your salary figures |
| `config/settings.yml` | Base year, working hours |
| `src/fetch_cpi.py` | CPI data source (swap Eurostat for BFS if their API becomes accessible) |
| `src/build_dashboard.py` | Dashboard appearance, chart types, extra KPIs |

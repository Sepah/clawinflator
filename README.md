# 🇨🇭 Swiss Salary Tracker

**Your salary, adjusted for Swiss inflation — updated automatically every month.**

---

## 👀 View the dashboard

**[Open dashboard →](https://sepah.github.io/clawinflator/)**

Or open locally: `dashboard/index.html` in any browser.

---

## ▶️ Run an update right now

**Option A — from GitHub (no computer needed):**
1. Go to [Actions tab](https://github.com/Sepah/clawinflator/actions)
2. Click **"Monthly salary tracker update"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Done — dashboard updates in ~1 minute

**Option B — from your computer:**
```bash
pip install -r requirements.txt   # first time only
python src/main.py
```
Then open `dashboard/index.html`.

---

## ✏️ Update your salary

Edit one file: **`config/salary_inputs.csv`**

```
year,monthly_chf,annual_chf
2023,7300,94900
2024,7450,96850
2025,7600,98800
2026,8100,105300   ← change this line, or add a new year
```

Then either run the pipeline (Option A or B above) to apply the change.

---

## 📅 Automatic updates

The dashboard **auto-updates on the 5th of every month** — no action needed.
It pulls the latest Swiss CPI from Eurostat and rebuilds everything.

---

## 📊 What the dashboard shows

| Metric | What it means |
|--------|---------------|
| **Nominal salary** | Your actual contractual salary |
| **Real salary** | What your salary is worth in 2023 money |
| **Nominal hourly** | Salary ÷ 2,184 hours/year (42 h/week) |
| **Real hourly** | Hourly rate in 2023 purchasing power |
| **Nominal raise vs 2023** | % increase before inflation |
| **Real raise vs 2023** | % increase after inflation ← the one that matters |
| **Annual gain/loss** | CHF you're ahead or behind vs 2023 purchasing power |
| **Cumulative inflation** | How much prices have risen since 2023 |

---

## 🔧 One-time GitHub Pages setup

Only needed once, then the live dashboard link works forever:

1. Go to repo **Settings → Pages**
2. Set Source to **GitHub Actions**
3. Run the workflow once (see "Run right now" above)

---

## 📁 Key files

| File | Purpose |
|------|---------|
| `config/salary_inputs.csv` | **Your salary data — edit this** |
| `dashboard/index.html` | The dashboard (auto-generated) |
| `data/processed/salary_tracker.xlsx` | Excel version of all data |
| `data/processed/summary.json` | Latest numbers as JSON |

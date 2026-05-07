# 🇨🇭 Swiss Salary Tracker

Your salary, adjusted for Swiss inflation — updated automatically every month.

| | |
|---|---|
| 📊 **[Open dashboard](https://sepah.github.io/clawinflator/)** | View your live salary tracker |
| ▶️ **[Run update now](https://github.com/Sepah/clawinflator/actions/workflows/monthly-update.yml)** | Fetch latest CPI & rebuild dashboard |
| ✏️ **[Edit salary figures](https://github.com/Sepah/clawinflator/edit/main/config/salary_inputs.csv)** | Update your salary data |

> **To run an update:** click the link above → **Run workflow** button (top right) → **Run workflow**

---

## 🚀 First-time setup (do this once)

You need to enable GitHub Pages so the dashboard has a live URL.

1. Open your repo on GitHub
2. Click **Settings** (top menu)
3. Click **Pages** in the left sidebar
4. Under **Source** → select **GitHub Actions**
5. Click **Save**

Then trigger the first run:

1. Click **Actions** (top menu)
2. Click **Monthly salary tracker update** (left sidebar)
3. Click **Run workflow** → **Run workflow**
4. Wait ~60 seconds

Your dashboard is now live at:
**`https://sepah.github.io/clawinflator/`**

---

## 🔄 Refresh the dashboard anytime

1. Click **Actions** (top menu)
2. Click **Monthly salary tracker update**
3. Click **Run workflow** → **Run workflow**

*(It also runs automatically on the 5th of every month — no action needed.)*

---

## ✏️ Update your salary figures

1. Open **`config/salary_inputs.csv`** in the repo
2. Click the pencil ✏️ icon to edit
3. Change the numbers or add a new year row:
   ```
   2027,8500,110500
   ```
4. Click **Commit changes**
5. Then run the workflow (see above) to rebuild the dashboard

---

## 📊 What the dashboard shows

| Metric | What it means |
|--------|---------------|
| **Nominal salary** | Your actual contractual salary |
| **Real salary** | What your salary is worth in 2023 money |
| **Nominal raise vs 2023** | % increase before inflation |
| **Real raise vs 2023** | % increase after inflation ← the one that matters |
| **Annual gain/loss** | CHF you're ahead or behind vs 2023 purchasing power |
| **Cumulative inflation** | How much Swiss prices have risen since 2023 |
| **Hourly rate** | Salary ÷ 2,184 h/year (42 h/week × 52 weeks) |

CPI data is pulled automatically from Eurostat every run.

---

## 📁 Key files

| File | What it is |
|------|-----------|
| `config/salary_inputs.csv` | **Your salary data — the only file you need to edit** |
| `dashboard/index.html` | The dashboard (rebuilt automatically) |
| `data/processed/salary_tracker.xlsx` | Excel download with all data |

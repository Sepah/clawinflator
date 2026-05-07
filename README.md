# 🇨🇭 Swiss Salary Tracker

Your salary, adjusted for Swiss inflation — updated automatically every month.

| | |
|---|---|
| 🇨🇭 **[Switzerland dashboard](https://sepah.github.io/clawinflator/)** | Your Swiss salary tracker |
| 🇬🇧 **[UK dashboard](https://sepah.github.io/clawinflator/uk.html)** | UK salary tracker |
| ▶️ **[Run update now](https://github.com/Sepah/clawinflator/actions/workflows/monthly-update.yml)** | Fetch latest CPI & rebuild both dashboards |
| ✏️ **[Edit Swiss salary](https://github.com/Sepah/clawinflator/edit/main/config/salary_inputs.csv)** · **[Edit UK salary](https://github.com/Sepah/clawinflator/edit/main/config/salary_inputs_uk.csv)** | Update your salary data |

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

There is also an **interactive calculator** on each dashboard — anyone can plug in their own salary, weekly hours and base year and see live calculations. No coding needed.

---

## 🌍 Region assumptions

| | 🇨🇭 Switzerland | 🇬🇧 United Kingdom |
|---|---|---|
| Currency | CHF | GBP (£) |
| Standard week | 42 h | 37.5 h *(UK full-time)* |
| Annual hours | 2,184 | 1,950 |
| Base year | 2023 | 2023 |
| CPI source | Eurostat HICP (CH, all-items) | ONS CPI All-Items (D7BT) |
| CPI base | 2015 = 100 | 2015 = 100 |

**UK salary placeholder:** the file `config/salary_inputs_uk.csv` ships with a representative UK upper-mid salary trajectory (£45k → £50k, 2023→2026). Edit it with your real figures.

**UK working hours assumption:** 37.5 h/week × 52 = 1,950 h/year is the standard UK full-time benchmark. Many contracts are 37 or 40 — adjust in `src/regions.py` if needed.

---

## 📁 Key files

| File | What it is |
|------|-----------|
| `config/salary_inputs.csv` | **Swiss salary data — edit this** |
| `config/salary_inputs_uk.csv` | **UK salary data — edit this** |
| `dashboard/index.html` | Switzerland dashboard (auto-generated) |
| `dashboard/uk.html` | UK dashboard (auto-generated) |
| `data/processed/salary_tracker.xlsx` | Excel download with all data |

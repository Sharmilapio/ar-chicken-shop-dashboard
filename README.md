# A.R Chicken Shop – Interactive Dashboard

## How to run (Windows 10)

1. Open **Command Prompt** in this folder (the one with `app.py`).
2. Create and activate a virtual environment (one-time setup):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the dashboard:
   ```
   streamlit run app.py
   ```
5. It will automatically open in your browser at `http://localhost:8501`.
   Next time, you only need steps 2 (activate) and 4 (run).

## How to use it

- On the homepage, you will see a broiler-only shop view with fresh chicken
  details, evening snack notes, and the bulk discount offer.
- **Buy 10 kg or more** and the app applies **₹10 off per kg** to the broiler price.
- **Evening snacks** such as Chilli Chicken are highlighted after 5 PM.
- **Dashboard charts are shown only after login** using the sidebar login form.
- **Upload your dataset** from the left sidebar (CSV file) — **any column
  names are fine now**, you don't need to rename anything in your file.
- **Step 1 — Match your columns:** the app shows a one-time screen where you
  pick, from dropdowns, which of your file's columns means Date, Chicken Type,
  Sold KG, Cost per KG, Wastage KG, and Festival/Normal. If a column doesn't
  exist in your file (e.g. no wastage tracked), choose
  **"-- Not in my file --"** and enter a fixed value instead. Click **Confirm
  mapping & build dashboard** once done.
- **Edit rates** (₹/kg) in the sidebar — the app automatically detects every
  chicken/item type found in your data and gives you a rate box for each one.
  Change any rate and every chart/KPI recalculates instantly, no re-upload.
- **Filter** by month, weekday/weekend, or festival/normal.
- **Upload a new month's CSV** any time to see that month's numbers, and check
  the "Monthly Profit Comparison" section to compare months side by side. Use
  **"🔁 Upload a different file / change mapping"** in the sidebar to remap a
  new file with a different layout.
- No file yet? Click **Generate Demo Dataset** in the sidebar to explore the
  dashboard with sample data, or open `sample_dataset.csv` (included) and
  upload that.

## What your CSV needs to contain (column names can be anything)

| What it means | Example column names that would work |
|---|---|
| Date of sale | `Date`, `Sale Date`, `Day` |
| Chicken type / item | `Chicken_Type`, `Item`, `Product` |
| Quantity sold (kg) | `Sold_KG`, `Qty Sold`, `KG Sold` |
| Your cost per kg | `Cost_Per_KG`, `Purchase Rate`, `Cost` |
| Wastage (kg) | `Wastage_KG`, `Waste`, `Loss KG` |
| Festival or Normal day | `Festival_Normal`, `Day Type`, `Occasion` |

If a concept isn't tracked in your file at all (e.g. you never recorded
wastage), just tell the mapping screen it's "Not in my file" — it'll use a
default value instead of blocking you.

The selling **rate per kg** is NOT in the file — that's what you control live
from the sidebar, so you can test "what if I raise Broiler to ₹190/kg?"
instantly.
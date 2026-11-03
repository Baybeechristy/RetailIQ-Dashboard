# RetailIQ — Sales Performance & Customer Intelligence

Interactive local dashboard and raw data profiling for the public [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail).

## Quick start

1. Download **Online Retail.xlsx** from the UCI page above.
2. Save it in this folder as `Online Retail.xlsx` (or upload it in the app).
3. In Terminal, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

Windows activation: `.venv\\Scripts\\activate`.

## Workflow

- **1 · Raw data profile:** missingness, duplicates, cancellations, invalid values, date range, data types. Exports real audit reports as JSON and CSV. The raw data are unchanged.
- **2 · Dashboard:** four interactive Plotly charts after you explicitly acknowledge the analytical inclusion rules.

The exploratory dashboard uses **gross completed-line sales** (`Quantity * UnitPrice`) and excludes cancellations, non-positive quantities or prices and invalid dates. Missing CustomerID records remain included for overall sales, but not customer-specific analysis. **It does not compute net revenue** and does not deduplicate source records. The raw workbook is not modified.

## Publish after testing

After verifying the counts and approving a cleaning strategy, one publishing option is Streamlit Community Cloud from a GitHub repository. Do not include confidential data. The source workbook is public and CC BY 4.0, but attribution is still required.

## Citation

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33 · CC BY 4.0.

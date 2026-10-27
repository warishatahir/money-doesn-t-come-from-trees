# money doesn't come from trees 🌱

A spending tracker I built after analyzing my own bank statements and
realizing a third of my spending was food and coffee.

**What it does**
- Reads a CSV of transactions, including Bank of America downloads
- Categorizes purchases in SQL: a keyword rules table joined with `LIKE`,
  using a window function (`ROW_NUMBER` + `QUALIFY`) to keep the highest-priority match
- Runs the analysis as SQL queries in DuckDB: category totals, share of total
  spending (window function), monthly trends, and top merchants.
  Turn on "Show the SQL" in the sidebar to see every query
- Lets you fix any category by hand, and every chart updates
- "What if" calculators for cutting coffee runs and eating out

**Tech:** SQL (DuckDB), Python, pandas, Altair, Streamlit

The public version shows made-up sample data. Uploaded files stay in the
browser session and are never saved.

**Run it locally**
```
pip install -r requirements.txt
streamlit run app.py
```

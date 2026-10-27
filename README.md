# Where my money goes

A small Streamlit app that turns a bank CSV into a spending breakdown.
I built it after analyzing my own statements and realizing a third of my
spending was food and coffee.

**What it does**
- Reads a CSV of transactions (including Bank of America downloads)
- Sorts each purchase into a category with keyword rules
- Lets you fix any category by hand, and every chart updates
- Shows totals, a coffee tracker, month-by-month trends, and a drill-down by category

**Tech:** Python, pandas, Altair, Streamlit

The public version shows made-up sample data. Uploaded files stay in the
browser session and are never saved.

**Run it locally**
```
pip install -r requirements.txt
streamlit run app.py
```

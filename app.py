# Spending tracker: upload a bank CSV and see where the money goes.
# Run locally with:  streamlit run app.py

import io
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Where my money goes", page_icon="☕", layout="wide")

# ---------------------------------------------------------------------------
# 1. Category rules. First match wins, so order matters.
#    To recategorize a store, move its keyword to a different list.
# ---------------------------------------------------------------------------
RULES = {
    "Transfers": ["transfer"],
    "Tuition": ["tuition", "GEO WASHINGTON U"],
    "Income": ["payroll", "cashreward", "rewards", "interest"],
    "Refunds": ["refund", "reimburse"],
    "Coffee": ["coffee", "peet", "cuppi", "dunkin", "dd/br", "arkibuna", "shotted",
               "cafein", "starbucks"],
    "Eating out": ["paris baguette", "point chaud", "chick-fil-a", "absurd", "taco bell",
                   "panera", "2200 penn", "layered", "ballywhack", "dinner", "wawa", "7-eleven"],
    "Groceries": ["walmart", "wal-mart", "whole", "wholefds", "food lion", "safeway",
                  "trader joe"],
    "Transportation": ["metro", "shell", "parking", "gas"],
    "Shopping & beauty": ["ulta", "barnes", "tiktok", "cvs", "h&m", "primark"],
    "Subscriptions": ["subscription", "apple.com", "anthropic", "claude", "icloud"],
    "Outings": ["imperial farms", "kings dominion", "shenandoah"],
    "Friends & MSA": ["apple cash", "venmo", "zelle"],
}
NOT_SPENDING = ["Transfers", "Tuition", "Income", "Refunds"]
ALL_CATEGORIES = list(RULES) + ["Other"]


def categorize(description: str) -> str:
    text = str(description).lower()
    for category, keywords in RULES.items():
        if any(k.lower() in text for k in keywords):
            return category
    return "Other"


# ---------------------------------------------------------------------------
# 2. Loading. Works with this app's simple format (date, description, amount)
#    and with Bank of America CSV downloads, which have summary lines on top.
# ---------------------------------------------------------------------------
def load_csv(raw: bytes) -> pd.DataFrame:
    lines = raw.decode("utf-8-sig", errors="ignore").splitlines()
    header_row = next(
        (i for i, line in enumerate(lines)
         if "date" in line.lower() and "description" in line.lower()),
        0,
    )
    df = pd.read_csv(io.StringIO("\n".join(lines[header_row:])))
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[["date", "description", "amount"]].dropna(subset=["amount"])
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    df["category"] = df["description"].apply(categorize)
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Page
# ---------------------------------------------------------------------------
st.title("Where my money goes")

with st.sidebar:
    st.header("Your data")
    uploaded = st.file_uploader("Upload a bank CSV", type="csv")
    st.caption("Needs date, description and amount columns. "
               "Spending is negative, money in is positive. "
               "Files stay in this session and are not saved.")

if uploaded is not None:
    data = load_csv(uploaded.getvalue())
    st.caption(f"Showing {uploaded.name}")
else:
    with open("sample_data.csv", "rb") as f:
        data = load_csv(f.read())
    st.info("Showing made-up sample data. Upload your own CSV in the sidebar.")

if data.empty:
    st.error("No transactions found. Check that the file has date, description "
             "and amount columns.")
    st.stop()

# Let the user fix categories by hand. Changes apply to everything below.
with st.expander("Fix categories"):
    st.caption("Click a category to change it. Everything below updates.")
    data = st.data_editor(
        data,
        column_config={
            "category": st.column_config.SelectboxColumn("category", options=ALL_CATEGORIES),
            "date": st.column_config.DateColumn("date", format="MMM D"),
            "amount": st.column_config.NumberColumn("amount", format="$%.2f"),
        },
        disabled=["date", "description", "amount"],
        hide_index=True,
        width="stretch",
    )

spending = data[(data["amount"] < 0) & (~data["category"].isin(NOT_SPENDING))].copy()
spending["spent"] = -spending["amount"]
income = data.loc[data["category"] == "Income", "amount"].sum()
coffee = spending[spending["category"] == "Coffee"]

# Headline numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric("Spent", f"${spending['spent'].sum():,.2f}")
c2.metric("Earned", f"${income:,.2f}")
c3.metric("Left over", f"${income - spending['spent'].sum():,.2f}")
c4.metric("Coffee", f"${coffee['spent'].sum():,.2f}")
c4.caption(f"{len(coffee)} runs")

# By category
st.subheader("By category")
by_cat = spending.groupby("category", as_index=False)["spent"].sum()
chart = (
    alt.Chart(by_cat)
    .mark_bar(cornerRadiusEnd=3)
    .encode(
        x=alt.X("spent:Q", title="Dollars"),
        y=alt.Y("category:N", sort="-x", title=None),
        tooltip=["category", alt.Tooltip("spent:Q", format="$,.2f")],
    )
    .properties(height=320)
)
st.altair_chart(chart, width="stretch")

# By month (only useful once there's more than one month)
spending["month"] = spending["date"].dt.to_period("M").astype(str)
if spending["month"].nunique() > 1:
    st.subheader("Month by month")
    by_month = spending.groupby(["month", "category"], as_index=False)["spent"].sum()
    st.altair_chart(
        alt.Chart(by_month).mark_bar().encode(
            x=alt.X("month:N", title=None),
            y=alt.Y("spent:Q", title="Dollars"),
            color=alt.Color("category:N", title=None),
            tooltip=["month", "category", alt.Tooltip("spent:Q", format="$,.2f")],
        ).properties(height=320),
        width="stretch",
    )

# Look inside one category
st.subheader("Look inside a category")
pick = st.selectbox("Category", sorted(spending["category"].unique()))
detail = spending[spending["category"] == pick][["date", "description", "spent"]]
st.dataframe(
    detail,
    column_config={
        "date": st.column_config.DateColumn("date", format="MMM D"),
        "spent": st.column_config.NumberColumn("spent", format="$%.2f"),
    },
    hide_index=True,
    width="stretch",
)
st.caption(f"{len(detail)} purchases, ${detail['spent'].sum():,.2f} total")

# money doesn't come from trees 🌱
# A spending tracker: Python loads the CSV, SQL (DuckDB) does the analysis,
# Streamlit shows it. Run locally with:  streamlit run app.py

import io
import duckdb
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="money doesn't come from trees", page_icon="🌱", layout="wide")

# ---------------------------------------------------------------------------
# Look and feel
# ---------------------------------------------------------------------------
ROSE, COCOA, BLUSH = "#D9577F", "#3A2A30", "#FFF5F7"
CATEGORY_COLORS = {
    "Coffee": "#B07D62", "Eating out": "#F29CB4", "Groceries": "#8DB596",
    "Transportation": "#9CC9E8", "Shopping & beauty": "#C9A7E8", "Subscriptions": "#F6D47A",
    "Outings": "#F7B58A", "Friends & MSA": "#E8A0A0", "Other": "#C8C0C3",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,600,100&family=Nunito:wght@400;600;800&display=swap');
html, body, [class*="css"], .stMarkdown, p, label { font-family: 'Nunito', sans-serif; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; font-variation-settings: 'SOFT' 100; color: #3A2A30 !important; }
h1 { font-size: 3rem !important; letter-spacing: -0.02em; }
.stApp { background: #FFF5F7; }
section[data-testid="stSidebar"] { background: #FFE3EA; }
header[data-testid="stHeader"] { background: #FFF5F7; }
.stApp p, .stApp label, .stApp li, .stApp summary, .stApp small,
[data-testid="stWidgetLabel"] *, [data-testid="stMetricLabel"] *,
[data-testid="stCaptionContainer"] *, [data-testid="stExpander"] summary * { color: #3A2A30 !important; }
[data-testid="stCaptionContainer"] * { color: #7A5F68 !important; }
[data-testid="stFileUploaderDropzone"] { background: white !important; }
[data-testid="stFileUploaderDropzone"] * { color: #3A2A30 !important; }
[data-testid="stFileUploaderDropzone"] button { background: #D9577F !important; border: none !important; }
[data-testid="stFileUploaderDropzone"] button * { color: white !important; }
[data-testid="stExpander"] details { background: white; border-color: #F6C6D4 !important; border-radius: 16px; }
.stApp div[data-baseweb="select"] > div, .stApp input { background: white !important; color: #3A2A30 !important; }
div[data-testid="stMetric"] {
  background: white; border: 2px solid #F6C6D4; border-radius: 22px; padding: 18px 20px;
}
div[data-testid="stMetricValue"] { font-family: 'Fraunces', serif; color: #3A2A30; }
.sub { color: #7A5F68; font-size: 1.1rem; margin-top: -0.6rem; }
.top5 { width: 100%; border-collapse: collapse; background: white; border-radius: 16px;
        overflow: hidden; box-shadow: 0 0 0 2px #F6C6D4; margin-bottom: 1rem; }
.top5 th, .top5 td { padding: 12px 18px; text-align: left; color: #3A2A30; border: none; }
.top5 th { background: #FFE3EA; font-weight: 800; }
.top5 tr + tr td { border-top: 1px solid #F6DCE3; }
.top5 td:nth-child(2), .top5 td:nth-child(3), .top5 th:nth-child(2), .top5 th:nth-child(3) { text-align: right; }
.big-save { font-family: 'Fraunces', serif; font-size: 2.6rem; color: #D9577F; line-height: 1.1; }
div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"] {
  background: white; border: 2px solid #F6C6D4 !important; border-radius: 24px;
  padding: 22px 22px 14px; position: relative; overflow: visible;
}
div[data-testid="stElementContainer"]:has(.card-mark) { position: static; height: 0; margin: 0; }
.corner-sticker {
  position: absolute; top: -26px; right: 18px; z-index: 5;
  border: 4px solid white; border-radius: 999px; padding: 8px 16px;
  font-weight: 800; font-size: 0.95rem; color: #3A2A30; white-space: nowrap;
  box-shadow: 0 4px 0 rgba(58, 42, 48, 0.12), 0 0 0 2px #F6C6D4;
}
.tilt-l { transform: rotate(-4deg); } .tilt-r { transform: rotate(4deg); }
.pink { background: #FFD9E4; } .green { background: #E3F1E5; } .yellow { background: #FFF1C9; }
.jar-wrap { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.jar-lid { width: 110px; height: 16px; background: #E8A0B4; border-radius: 6px; }
.jar {
  width: 150px; height: 190px; border: 4px solid #E8A0B4; border-top: none;
  border-radius: 0 0 36px 36px; position: relative; overflow: hidden; background: #FFF9FA;
}
.jar-fill {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(180deg, #F29CB4, #D9577F); transition: height 0.6s ease;
}
.jar-pct { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-family: 'Fraunces', serif; font-size: 1.8rem; color: #3A2A30; }
.badges { display: flex; flex-wrap: wrap; gap: 12px; }
.badge { border-radius: 999px; padding: 10px 18px; font-weight: 800; border: 2px solid #F6C6D4; }
.badge.on { background: #D9577F; color: white; border-color: #D9577F; }
.badge.off { background: #FBF3F5; color: #B9A3AA; border-style: dashed; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Category rules, stored as a table so SQL can join on it.
# Lower priority number wins when two keywords match.
# ---------------------------------------------------------------------------
RULES = {
    "Transfers": ["transfer"],
    "Tuition": ["tuition", "geo washington u"],
    "Income": ["payroll", "cashreward", "rewards", "interest"],
    "Refunds": ["refund", "reimburse"],
    "Coffee": ["coffee", "peet", "cuppi", "dunkin", "dd/br", "arkibuna", "shotted",
               "cafein", "starbucks"],
    "Eating out": ["paris baguette", "point chaud", "chick-fil-a", "absurd", "taco bell",
                   "panera", "2200 penn", "layered", "ballywhack", "dinner", "wawa", "7-eleven"],
    "Groceries": ["walmart", "wal-mart", "whole", "wholefds", "food lion", "safeway", "trader joe"],
    "Transportation": ["metro", "shell", "parking", "gas"],
    "Shopping & beauty": ["ulta", "barnes", "tiktok", "cvs", "h&m", "primark"],
    "Subscriptions": ["subscription", "apple.com", "anthropic", "claude", "icloud"],
    "Outings": ["imperial farms", "kings dominion", "shenandoah"],
    "Friends & MSA": ["apple cash", "venmo", "zelle"],
}
NOT_SPENDING = ["Transfers", "Tuition", "Income", "Refunds"]
rules = pd.DataFrame(
    [(kw, cat, p) for p, (cat, kws) in enumerate(RULES.items()) for kw in kws],
    columns=["keyword", "category", "priority"],
)

# ---------------------------------------------------------------------------
# SQL. Each query is a named string so the app can show it on screen.
# ---------------------------------------------------------------------------
SQL_CATEGORIZE = """
-- Match every transaction to a keyword rule; if several match, keep the
-- highest-priority one (window function + QUALIFY).
SELECT t.id, t.date, t.description, t.amount,
       COALESCE(r.category, 'Other') AS category
FROM transactions t
LEFT JOIN rules r
  ON lower(t.description) LIKE '%' || r.keyword || '%'
QUALIFY ROW_NUMBER() OVER (PARTITION BY t.id ORDER BY r.priority) = 1
ORDER BY t.date
"""

SQL_SPENDING_VIEW = f"""
-- Everyday spending only: money out, minus transfers, tuition, etc.
CREATE OR REPLACE VIEW spending AS
SELECT date, description, category,
       -amount AS spent,
       date_trunc('month', date) AS month,
       strftime(date, '%B ''%y') AS month_label,
       dayname(date) AS weekday
FROM categorized
WHERE amount < 0
  AND category NOT IN ({", ".join(f"'{c}'" for c in NOT_SPENDING)})
"""

SQL_SUMMARY = """
-- Headline numbers, plus how many days the data covers
SELECT
  (SELECT SUM(spent) FROM spending)                                AS spent,
  (SELECT COALESCE(SUM(amount), 0) FROM categorized
     WHERE category = 'Income')                                    AS earned,
  (SELECT COUNT(*) FROM spending WHERE category = 'Coffee')        AS coffee_runs,
  (SELECT COALESCE(SUM(spent), 0) FROM spending
     WHERE category = 'Coffee')                                    AS coffee_spent,
  (SELECT COALESCE(SUM(spent), 0) FROM spending
     WHERE category = 'Eating out')                                AS eating_out,
  (SELECT date_diff('day', MIN(date), MAX(date)) + 1 FROM categorized) AS days
"""

SQL_BY_CATEGORY = """
-- Total per category and its share of all spending
SELECT category,
       ROUND(SUM(spent), 2) AS spent,
       COUNT(*) AS purchases,
       ROUND(100 * SUM(spent) / SUM(SUM(spent)) OVER (), 1) AS pct
FROM spending
GROUP BY category
ORDER BY spent DESC
"""

SQL_BY_MONTH = """
-- Category totals per calendar month
SELECT month, month_label, category, ROUND(SUM(spent), 2) AS spent
FROM spending
GROUP BY month, month_label, category
ORDER BY month
"""

SQL_TOP_PLACES = """
-- Where I go most, ranked by total spent
SELECT description AS place, COUNT(*) AS visits, ROUND(SUM(spent), 2) AS total
FROM spending
GROUP BY description
ORDER BY total DESC
LIMIT 5
"""


def load_csv(raw: bytes) -> pd.DataFrame:
    """Read a simple date/description/amount CSV or a Bank of America download."""
    lines = raw.decode("utf-8-sig", errors="ignore").splitlines()
    header = next((i for i, l in enumerate(lines)
                   if "date" in l.lower() and "description" in l.lower()), 0)
    df = pd.read_csv(io.StringIO("\n".join(lines[header:])))
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[["date", "description", "amount"]]
    df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[$,]", "", regex=True),
                                 errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "amount"]).reset_index(drop=True)
    df["id"] = df.index
    return df


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("your data")
    uploaded = st.file_uploader("Upload a bank CSV", type="csv")
    st.caption("Needs date, description and amount columns. Spending is negative. "
               "Files stay in this session and are never saved.")
    show_sql = st.toggle("Show the SQL behind each section", value=False)

raw = uploaded.getvalue() if uploaded else open("sample_data.csv", "rb").read()
transactions = load_csv(raw)
if transactions.empty:
    st.error("No transactions found. Check that the file has date, description and amount columns.")
    st.stop()

con = duckdb.connect()
con.register("transactions", transactions)
con.register("rules", rules)


def sql(query: str) -> pd.DataFrame:
    if show_sql:
        st.code(query.strip(), language="sql")
    return con.execute(query).df()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("money doesn't come from trees 🌱")
st.markdown('<p class="sub">a little audit of where it actually went</p>', unsafe_allow_html=True)
if not uploaded:
    st.info("Showing made-up sample data. Upload your own CSV in the sidebar.")

categorized = sql(SQL_CATEGORIZE)
with st.expander("Fix categories"):
    st.caption("Click a category to change it. Everything below updates.")
    categorized = st.data_editor(
        categorized,
        column_config={
            "id": None,
            "category": st.column_config.SelectboxColumn(
                "category", options=list(RULES) + ["Other"]),
            "date": st.column_config.DateColumn("date", format="MMM D"),
            "amount": st.column_config.NumberColumn("amount", format="$%.2f"),
        },
        disabled=["date", "description", "amount"], hide_index=True, width="stretch",
    )
con.register("categorized", categorized)
con.execute(SQL_SPENDING_VIEW)
if show_sql:
    st.code(SQL_SPENDING_VIEW.strip(), language="sql")

s = sql(SQL_SUMMARY).iloc[0]
spent, earned, days = float(s.spent or 0), float(s.earned), int(s.days)
coffee_runs, coffee_spent = int(s.coffee_runs), float(s.coffee_spent)
per_month = 30.4 / days

c1, c2, c3, c4 = st.columns(4)
c1.metric("spent", f"${spent:,.2f}")
c2.metric("earned", f"${earned:,.2f}")
c3.metric("left over", f"${earned - spent:,.2f}")
c4.metric("coffee", f"${coffee_spent:,.2f}")
c4.caption(f"{coffee_runs} runs")

# --- by category -----------------------------------------------------------
st.header("where it went")
by_cat = sql(SQL_BY_CATEGORY)
color = alt.Color("category:N", legend=None,
                  scale=alt.Scale(domain=list(CATEGORY_COLORS), range=list(CATEGORY_COLORS.values())))
st.altair_chart(
    alt.Chart(by_cat).mark_bar(cornerRadiusEnd=10, height=26).encode(
        x=alt.X("spent:Q", title=None, axis=alt.Axis(format="$,.0f", grid=False, tickCount=6)),
        y=alt.Y("category:N", sort="-x", title=None, axis=alt.Axis(labelFontSize=14, labelLimit=200)),
        color=color,
        tooltip=["category", alt.Tooltip("spent:Q", format="$,.2f"), "purchases",
                 alt.Tooltip("pct:Q", title="% of spending")],
    ).properties(height=alt.Step(40)).configure(background="#FFF5F7")
     .configure_view(strokeWidth=0)
     .configure_axis(labelColor="#3A2A30", titleColor="#3A2A30", domain=False, ticks=False),
    width="stretch", theme=None,
)

# --- by month --------------------------------------------------------------
by_month = sql(SQL_BY_MONTH)
if by_month["month"].nunique() > 1:
    st.header("month by month")
    st.altair_chart(
        alt.Chart(by_month).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=70).encode(
            x=alt.X("month_label:N", title=None,
                    sort=alt.SortField("month"), axis=alt.Axis(labelAngle=0, labelFontSize=14)),
            y=alt.Y("sum(spent):Q", title=None, axis=alt.Axis(format="$,.0f")),
            color=alt.Color("category:N", title=None,
                            scale=alt.Scale(domain=list(CATEGORY_COLORS),
                                            range=list(CATEGORY_COLORS.values()))),
            tooltip=["month_label", "category", alt.Tooltip("spent:Q", format="$,.2f")],
        ).properties(height=340).configure(background="#FFF5F7")
         .configure_view(strokeWidth=0)
         .configure_axis(labelColor="#3A2A30", titleColor="#3A2A30",
                         domain=False, ticks=False, gridColor="#F6DCE3")
         .configure_legend(labelColor="#3A2A30"),
        width="stretch", theme=None,
    )

# --- top places --------------------------------------------------------------
st.header("top 5 places")
top5 = sql(SQL_TOP_PLACES)
rows = "".join(
    f"<tr><td>{r.place}</td><td>{r.visits}</td><td>${r.total:,.2f}</td></tr>"
    for r in top5.itertuples()
)
st.markdown(f'<table class="top5"><tr><th>place</th><th>visits</th><th>total</th></tr>{rows}</table>',
            unsafe_allow_html=True)

# --- what if ------------------------------------------------------------------
st.header("what if")


def corner(text, color, tilt):
    st.markdown(f'<span class="card-mark"></span><div class="corner-sticker {color} {tilt}">{text}</div>',
                unsafe_allow_html=True)


coffee_month = coffee_spent * per_month
eating_month = float(s.eating_out) * per_month
left, right = st.columns(2, gap="large")

with left, st.container(border=True):
    if coffee_month > 60:
        corner("girl, you're spending too much on coffee ☕", "pink", "tilt-r")
    else:
        corner("coffee's under control", "green", "tilt-r")
    st.subheader("making coffee at home")
    treat_days = st.pills("Treat days: coffee out allowed",
                          ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                          selection_mode="multi", default=["Fri"]) or []
    home_cup = st.number_input("Cost of a coffee made at home", value=0.75, step=0.25, format="%.2f")
    runs_month = coffee_runs * per_month
    avg_cup = coffee_spent / coffee_runs if coffee_runs else 0
    treat_runs = min(len(treat_days) * 4.35, runs_month)
    new_coffee = treat_runs * avg_cup + (runs_month - treat_runs) * home_cup
    coffee_save = max(coffee_month - new_coffee, 0)
    st.markdown(f'<div class="big-save">${coffee_save:,.0f}/month</div>', unsafe_allow_html=True)
    st.caption(f"Coffee goes from \\${coffee_month:,.0f} to \\${new_coffee:,.0f} a month.")

with right, st.container(border=True):
    lunch_days = st.session_state.get("lunch_days", 3) or 0
    corner(f"{lunch_days} packed lunches a week", "yellow", "tilt-l")
    st.subheader("packing lunch")
    lunch_days = st.segmented_control("Days a week you pack lunch", [0, 1, 2, 3, 4, 5],
                                      default=3, key="lunch_days") or 0
    lunch_save = eating_month * lunch_days / 5
    st.markdown(f'<div class="big-save">${lunch_save:,.0f}/month</div>', unsafe_allow_html=True)
    st.caption(f"Eating out goes from \\${eating_month:,.0f} to \\${eating_month - lunch_save:,.0f} "
               "a month (assuming most of it happens on weekdays).")

# --- savings goal ----------------------------------------------------------------
monthly_save = coffee_save + lunch_save
st.header("what are you saving for?")
with st.container(border=True):
    g1, g2 = st.columns([3, 2], gap="large")
    goal_sticker = st.empty()
    with g1:
        goal_name = st.text_input("Goal", value="new laptop")
        goal_amount = st.number_input("How much it costs", value=1200, step=50, min_value=1)
        months_to_goal = goal_amount / monthly_save if monthly_save > 0 else None
        ahead = st.slider("Fast-forward", 0, 24, 3, format="%d months")
        saved = min(monthly_save * ahead, goal_amount)
        pct = saved / goal_amount
        if months_to_goal is None:
            st.markdown('<div class="big-save">pick a savings plan above</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="big-save">{goal_name} in {months_to_goal:.0f} months</div>',
                        unsafe_allow_html=True)
            st.caption(f"Saving \\${monthly_save:,.0f} a month. After {ahead} months: "
                       f"\\${saved:,.0f} of \\${goal_amount:,.0f}.")
        if pct >= 1:
            with goal_sticker:
                corner("goal reached!", "green", "tilt-r")
    with g2:
        st.markdown(f'''<div class="jar-wrap"><div class="jar-lid"></div>
            <div class="jar"><div class="jar-fill" style="height:{pct * 100:.0f}%"></div>
            <div class="jar-pct">{pct * 100:.0f}%</div></div></div>''', unsafe_allow_html=True)

# --- badges ------------------------------------------------------------------------
st.header("badges")
badges = [
    ("Friday-only coffee", len(treat_days) <= 1),
    ("home barista: no coffee out", len(treat_days) == 0),
    ("lunchbox club: 3+ days", lunch_days >= 3),
    ("full lunchbox: 5 days", lunch_days == 5),
    ("goal within a year", months_to_goal is not None and months_to_goal <= 12),
    ("spent less than you earned", earned - spent > 0),
]
st.markdown('<div class="badges">' + "".join(
    f'<span class="badge {"on" if got else "off"}">{"✓ " if got else ""}{name}</span>'
    for name, got in badges) + "</div>", unsafe_allow_html=True)
st.caption(f"{sum(g for _, g in badges)} of {len(badges)} unlocked. Change the plan above to unlock more.")

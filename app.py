from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------- Page setup -----------------------------
st.set_page_config(
    page_title="PhonePe Payment Insights",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f6f7fc; color: #17152b; }
    [data-testid="stHeader"] { background: rgba(246,247,252,0); }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }
    .brand { color: #673ab7; font-size: 1.8rem; font-weight: 800; letter-spacing: -1px; }
    .hero { background: linear-gradient(120deg,#f0e9ff,#ffffff); padding: 18px 22px;
            border-radius: 18px; border: 1px solid #e7ddfb; margin-bottom: 12px; }
    .hero h1 { font-size: 2rem; margin: 0; color: #17152b; }
    .hero p { color: #66627a; margin: 5px 0 0 0; }
    [data-testid="stMetric"] { background: white; border: 1px solid #eceaf3;
        padding: 15px 17px; border-radius: 15px; box-shadow: 0 3px 12px rgba(34,20,70,.05); }
    [data-testid="stMetricLabel"] { color: #66627a; }
    [data-testid="stMetricValue"] { color: #2c1858; }
    div[data-testid="stPlotlyChart"] { background: white; border: 1px solid #eceaf3;
        border-radius: 15px; padding: 8px; box-shadow: 0 3px 12px rgba(34,20,70,.04); }
    .insight { background: linear-gradient(135deg,#5520a5,#793bd0); color: white;
        padding: 18px 20px; border-radius: 16px; margin-bottom: 10px; }
    .insight h3 { color: white; margin-top: 0; }
    .small-note { color: #77728b; font-size: .85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_FILE = Path(__file__).parent / "Phonepe-Final-Dataset.xlsx"


# ----------------------------- Data loading -----------------------------
@st.cache_data
def load_data(file_path: str):
    users = pd.read_excel(file_path, sheet_name="All_Users")
    transactions = pd.read_excel(file_path, sheet_name="All_Transactions")

    users["Join_Date"] = pd.to_datetime(users["Join_Date"], errors="coerce")
    transactions["Date"] = pd.to_datetime(transactions["Date"], errors="coerce")
    transactions["Amount"] = pd.to_numeric(transactions["Amount"], errors="coerce").fillna(0)

    # Join age and customer name to each transaction for user-level analysis.
    data = transactions.merge(
        users[["User_ID", "Name", "Age", "Join_Date"]],
        on="User_ID",
        how="left",
    )
    data["Age Segment"] = pd.cut(
        data["Age"],
        bins=[0, 17, 25, 35, 45, 60, float("inf")],
        labels=["Below 18", "18-25", "26-35", "36-45", "46-60", "Above 60"],
        include_lowest=True,
    )
    data["Month"] = data["Date"].dt.strftime("%b")
    data["Month Sort"] = data["Date"].dt.month
    data["Month-Year"] = data["Date"].dt.to_period("M").astype(str)
    data["Day Type"] = data["Date"].dt.dayofweek.map(
        lambda day: "Weekend" if day >= 5 else "Weekday"
    )
    return users, data


if not DATA_FILE.exists():
    st.error(
        "Dataset file not found. Upload **Phonepe-Final-Dataset.xlsx** "
        "to the same GitHub repository folder as app.py."
    )
    st.stop()

try:
    users, all_data = load_data(str(DATA_FILE))
except Exception as exc:
    st.error(f"Could not read the Excel dataset: {exc}")
    st.info(
        "Check that the workbook is named Phonepe-Final-Dataset.xlsx and "
        "contains sheets named All_Users and All_Transactions."
    )
    st.stop()


# ----------------------------- Header and filters -----------------------------
st.markdown(
    """
    <div class="hero">
      <div class="brand">◉ PhonePe</div>
      <h1>Payment insights, powering Bharat</h1>
      <p>Secure. Simple. Seamless. &nbsp; | &nbsp; Interactive transaction analytics</p>
    </div>
    """,
    unsafe_allow_html=True,
)

f1, f2, f3 = st.columns([1, 1.5, 1])
with f1:
    month_options = ["All"] + [
        pd.Timestamp(month=month, year=2000, day=1).strftime("%b")
        for month in range(1, 13)
    ]
    selected_month = st.selectbox("Month", month_options, index=0)
with f2:
    status_options = ["All"] + sorted(all_data["Payment_Status"].dropna().astype(str).unique())
    selected_status = st.selectbox("Payment Status", status_options, index=0)
with f3:
    service_options = ["All"] + sorted(all_data["Service"].dropna().astype(str).unique())
    selected_service = st.selectbox("Service", service_options, index=0)

filtered = all_data.copy()
if selected_month != "All":
    filtered = filtered[filtered["Month"] == selected_month]
if selected_status != "All":
    filtered = filtered[filtered["Payment_Status"].astype(str) == selected_status]
if selected_service != "All":
    filtered = filtered[filtered["Service"].astype(str) == selected_service]

if filtered.empty:
    st.warning("No transactions match the selected filters. Please change a filter.")
    st.stop()

successful = filtered[filtered["Payment_Status"].astype(str).str.lower() == "successful"]
total_transactions = len(filtered)
total_value = filtered["Amount"].sum()
unique_users = filtered["User_ID"].nunique()
success_rate = (len(successful) / total_transactions * 100) if total_transactions else 0

# ----------------------------- KPI cards -----------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Transactions", f"{total_transactions:,.0f}")
k2.metric("Total Transaction Value", f"₹{total_value:,.0f}")
k3.metric("Unique Users", f"{unique_users:,.0f}")
k4.metric("Successful Rate", f"{success_rate:.2f}%")

PURPLE = "#673ab7"
PURPLE_DARK = "#311b92"
PALETTE = ["#673ab7", "#9575cd", "#b39ddb", "#512da8", "#d1c4e9", "#7e57c2"]
chart_layout = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", color="#25213a"),
    margin=dict(l=25, r=20, t=55, b=35),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ----------------------------- Charts row 1 -----------------------------
left, right = st.columns([1.65, 1])

with left:
    st.subheader("Transactions Over Time")
    trend = (
        filtered.dropna(subset=["Date"])
        .groupby(pd.Grouper(key="Date", freq="MS"))
        .agg(Transactions=("Transaction_ID", "count"), Value=("Amount", "sum"))
        .reset_index()
    )
    fig_trend = px.area(
        trend, x="Date", y="Value",
        labels={"Date": "Month", "Value": "Transaction value (₹)"},
        color_discrete_sequence=[PURPLE],
    )
    fig_trend.update_traces(line=dict(width=2.5), fillcolor="rgba(103,58,183,0.25)")
    fig_trend.update_layout(**chart_layout, height=340)
    st.plotly_chart(fig_trend, use_container_width=True)

with right:
    st.subheader("Age Segment Contribution")
    age_data = (
        filtered.dropna(subset=["Age Segment"])
        .groupby("Age Segment", observed=False)
        .size().reset_index(name="Transactions")
    )
    age_data = age_data[age_data["Transactions"] > 0]
    if not age_data.empty:
        fig_age = px.pie(
            age_data, names="Age Segment", values="Transactions", hole=0.62,
            color_discrete_sequence=PALETTE,
        )
        fig_age.update_traces(textposition="outside", textinfo="percent")
        fig_age.update_layout(**chart_layout, height=340, showlegend=True,
                              legend=dict(orientation="v", y=0.5, x=1.0))
        st.plotly_chart(fig_age, use_container_width=True)
    else:
        st.info("Age data is not available for the selected records.")

# ----------------------------- Charts row 2 -----------------------------
c1, c2, c3 = st.columns([1, 1.35, 1])

with c1:
    st.subheader("Service Transaction Value")
    service_data = (
        filtered.groupby("Service", as_index=False)["Amount"].sum()
        .sort_values("Amount", ascending=False)
    )
    fig_service = px.bar(
        service_data, x="Service", y="Amount",
        color_discrete_sequence=[PURPLE],
        labels={"Service": "Service", "Amount": "Value (₹)"},
    )
    fig_service.update_layout(**chart_layout, height=330, xaxis_tickangle=-25)
    st.plotly_chart(fig_service, use_container_width=True)

with c2:
    st.subheader("Top 5 Users by Transaction Value")
    top_users = (
        filtered.groupby(["User_ID", "Name"], dropna=False, as_index=False)
        .agg(Transaction_Value=("Amount", "sum"),
             Transactions=("Transaction_ID", "count"))
        .sort_values("Transaction_Value", ascending=False)
        .head(5)
    )
    if not top_users.empty:
        fig_top = px.bar(
            top_users, x="Name", y="Transaction_Value",
            color_discrete_sequence=[PURPLE_DARK],
            labels={"Name": "User", "Transaction_Value": "Transaction value (₹)"},
            hover_data=["Transactions", "User_ID"],
        )
        fig_top.update_layout(**chart_layout, height=330, xaxis_tickangle=-15)
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.info("No user records found.")

with c3:
    st.subheader("Weekday vs Weekend Usage")
    day_data = filtered.groupby("Day Type").size().reset_index(name="Transactions")
    fig_day = px.pie(
        day_data, names="Day Type", values="Transactions", hole=0.62,
        color="Day Type",
        color_discrete_map={"Weekday": "#673ab7", "Weekend": "#b39ddb"},
    )
    fig_day.update_traces(textposition="outside", textinfo="percent+value")
    fig_day.update_layout(**chart_layout, height=330, showlegend=True)
    st.plotly_chart(fig_day, use_container_width=True)

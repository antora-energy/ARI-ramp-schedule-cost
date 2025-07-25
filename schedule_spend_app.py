import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

st.title("ARI Ramp Schedule & Cost")

# --- Input Section ---
st.subheader("Start Month")
start_date = st.date_input("", datetime(2025, 9, 1))

st.subheader("Furnaces")
total_furnaces_limit = st.number_input("Total number of furnaces to bring up", min_value=1, value=10)
furnaces_per_month = st.number_input("Number of furnaces to bring up per month", min_value=0, value=2)
weeks_per_furnace = st.number_input("Time to bring up each furnace (weeks)", min_value=1, value=2)
cost_per_furnace = st.number_input("Cost to bring up each furnace ($)", min_value=0, value=50000)
furnace_run_duration_days = st.number_input("Duration for a furnace run (days)", min_value=1, value=21)

st.subheader("Modules")
boards_per_module = st.number_input("Number of ARI boards per Module", min_value=1, value=50)

st.subheader("Boards")
max_boards_per_furnace = st.number_input("Maximum number of boards per furnace", min_value=1, value=200)
boards_per_fixture = st.number_input("Number of boards per fixture", min_value=1, value=4)

st.subheader("Fixtures")
fixtures_per_furnace = max_boards_per_furnace // boards_per_fixture
st.markdown(f"**Number of fixtures per furnace**: {fixtures_per_furnace}")
fixtures_per_week = st.number_input("Number of fixtures fabricated per week", min_value=0, value=50)
cost_per_fixture = st.number_input("Cost per fixture ($)", min_value=0, value=3000)

st.markdown(f"**Boards per furnace**: {boards_per_fixture * fixtures_per_furnace}")

months = st.slider("Number of months to simulate", min_value=1, max_value=12, value=6)

# --- Simulation ---
monthly_furnace_spend = []
monthly_fixture_spend = []
monthly_boards = []
monthly_spend = []
cumulative_boards = []
cumulative_furnaces = []
cumulative_fixtures_fabricated = []
limiters = []
monthly_modules = []
cumulative_modules = []

total_boards = 0
total_modules = 0
available_fixtures = 0
fixture_fabrication_rate = fixtures_per_week * 4
pending_furnaces = []  # (month_ready, count)
total_fixtures_fabricated = 0
online_furnaces = []  # list of (start_month, fixtures_per_furnace)
total_furnaces_brought_up = 0

for month in range(months):
    current_date = start_date + relativedelta(months=month)

    # Schedule new furnace bring-ups only if under limit
    if total_furnaces_brought_up < total_furnaces_limit:
        bringup_complete_month = month + weeks_per_furnace // 4
        if bringup_complete_month < months:
            pending_furnaces.append((bringup_complete_month, min(furnaces_per_month, total_furnaces_limit - total_furnaces_brought_up)))

    # Check which furnaces are now online and add them if fixtures are available
    newly_ready_furnaces = sum(count for m, count in pending_furnaces if m == month)
    pending_furnaces = [(m, c) for m, c in pending_furnaces if m > month]

    new_online = 0
    for _ in range(newly_ready_furnaces):
        if available_fixtures >= fixtures_per_furnace:
            available_fixtures -= fixtures_per_furnace
            online_furnaces.append((month, fixtures_per_furnace))
            total_furnaces_brought_up += 1
            new_online += 1

    # Spend for new furnaces
    furnace_spend = new_online * cost_per_furnace

    # Fabricate fixtures
    if total_fixtures_fabricated < fixtures_per_furnace * total_furnaces_limit:
        remaining_needed = fixtures_per_furnace * total_furnaces_limit - total_fixtures_fabricated
        fabricated = min(fixture_fabrication_rate, remaining_needed)
    else:
        fabricated = 0
    available_fixtures += fabricated
    total_fixtures_fabricated += fabricated
    fixture_spend = fabricated * cost_per_fixture

    # All online furnaces continue to run in perpetuity
    possible_boards = len(online_furnaces) * fixtures_per_furnace * boards_per_fixture
    if total_fixtures_fabricated >= fixtures_per_furnace * total_furnaces_limit and total_furnaces_brought_up < total_furnaces_limit:
        limiter = "Furnaces"
    elif total_furnaces_brought_up >= total_furnaces_limit and total_fixtures_fabricated >= fixtures_per_furnace * total_furnaces_limit:
        limiter = "None"
    elif available_fixtures >= len(online_furnaces) * fixtures_per_furnace and len(online_furnaces) < total_furnaces_limit:
        limiter = "Furnaces"
    elif available_fixtures < len(online_furnaces) * fixtures_per_furnace:
        limiter = "Fixtures"
    else:
        limiter = "None"

    boards_produced = possible_boards
    total_boards += boards_produced

    # Calculate modules
    modules_this_month = boards_produced // boards_per_module
    total_modules += modules_this_month

    # Total spend
    monthly_furnace_spend.append(furnace_spend)
    monthly_fixture_spend.append(fixture_spend)
    total_spend = furnace_spend + fixture_spend

    monthly_boards.append(boards_produced)
    monthly_spend.append(total_spend)
    cumulative_boards.append(total_boards)
    cumulative_furnaces.append(len(online_furnaces))
    cumulative_fixtures_fabricated.append(total_fixtures_fabricated)
    limiters.append(limiter)
    monthly_modules.append(modules_this_month)
    cumulative_modules.append(total_modules)

# --- Output Section ---
dates = [(start_date + relativedelta(months=i)).strftime("%b %Y") for i in range(months)]
df = pd.DataFrame({
    "Month": dates,
    "Cum Furnaces Available": cumulative_furnaces,
    "Cum Fixtures Available": cumulative_fixtures_fabricated,
    "Limiter": limiters,
    "Boards (per month)": monthly_boards,
    "Boards (cumulative)": cumulative_boards,
    "Modules (per month)": monthly_modules,
    "Modules (cumulative)": cumulative_modules
})



st.subheader("Production")
fig, ax1 = plt.subplots()
months_index = pd.date_range(start=start_date, periods=months, freq='MS')

ax1.bar(months_index, monthly_modules, label="Modules (monthly)", color='tab:green', alpha=0.6, width=20)
ax2 = ax1.twinx()
ax2.plot(months_index, cumulative_modules, label="Modules (cumulative)", color='tab:green')

ax1.set_xlabel("Month")
ax1.set_ylabel("Modules per month", color='tab:green')
ax2.set_ylabel("Cumulative Modules", color='tab:green')

fig.autofmt_xdate()
fig.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2)
st.pyplot(fig)

st.subheader("Spend")
fig_spend, ax1 = plt.subplots()
months_index = pd.date_range(start=start_date, periods=months, freq='MS')

ax1.bar(months_index, np.array(monthly_furnace_spend)/1e3, label="Furnaces (monthly)", color='tab:blue', alpha=0.6, width=20)
ax1.bar(months_index, np.array(monthly_fixture_spend)/1e3, label="Fixtures (monthly)", color='tab:orange', alpha=0.6, bottom=np.array(monthly_furnace_spend)/1e3, width=20)

ax2 = ax1.twinx()
furnace_cum = np.cumsum(monthly_furnace_spend)
fixture_cum = np.cumsum(monthly_fixture_spend)
total_spend_series = furnace_cum + fixture_cum
ax2.plot(months_index, total_spend_series / 1e6, label="Total (cumulative)", color='tab:green')

ax1.set_xlabel("Month")
ax1.set_ylabel("Monthly Spend (Thousands $)")
ax2.set_ylabel("Cumulative Spend (Millions $)")
fig_spend.autofmt_xdate()
fig_spend.tight_layout()
fig_spend.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2)
st.pyplot(fig_spend)

st.header("Results")
st.dataframe(df.set_index("Month"))



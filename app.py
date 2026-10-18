
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import datetime, timezone
from sqlalchemy import text
from database import get_engine


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Sri Lanka Weather Intelligence",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌦️ Sri Lanka Weather Intelligence")
st.caption(
    "Weather monitoring, historical trends and ETL monitoring "
    "across Sri Lanka's 25 districts"
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------
@st.cache_data(ttl=60)
def load_weather_data():
    engine = get_engine()

    try:
        query = text("""
            SELECT
                district,
                city,
                timestamp,
                temp_c,
                humidity,
                wind_kph,
                weather_condition,
                fetched_at
            FROM weather_readings
            ORDER BY timestamp ASC
        """)

        with engine.connect() as connection:
            df = pd.read_sql(query, connection)

        return df

    finally:
        engine.dispose()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.header("Dashboard Controls")

    if st.button("🔄 Refresh Data", use_container_width=True):
        load_weather_data.clear()
        st.rerun()

try:
    df = load_weather_data()

except Exception as exc:
    st.error("Could not connect to PostgreSQL or load weather data.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.info(
        "Check PostgreSQL service, .env settings and database connection."
    )
    st.stop()

if df.empty:
    st.warning("No weather records found. Run `python run_once.py` first.")
    st.stop()


# --------------------------------------------------
# DATA PREPARATION
# --------------------------------------------------
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)

df["temp_c"] = pd.to_numeric(df["temp_c"], errors="coerce")
df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
df["wind_kph"] = pd.to_numeric(df["wind_kph"], errors="coerce")

df = df.dropna(subset=["district", "timestamp"])

latest = (
    df.sort_values("timestamp")
    .drop_duplicates(subset=["district"], keep="last")
    .copy()
)

districts = sorted(latest["district"].dropna().unique().tolist())

with st.sidebar:
    selected_districts = st.multiselect(
        "Select districts",
        options=districts,
        default=districts,
    )

    st.divider()
    st.subheader("Historical Period")

    period = st.selectbox(
        "Select time range",
        ["Last 24 hours", "Last 7 days", "Last 30 days", "All records"],
        index=2,
    )

    st.caption(f"Database records: {len(df):,}")
    st.caption(f"Districts available: {len(districts)}")


if not selected_districts:
    st.warning("Select at least one district from the sidebar.")
    st.stop()


# --------------------------------------------------
# LATEST WEATHER
# --------------------------------------------------
filtered_latest = latest[
    latest["district"].isin(selected_districts)
].copy()

st.subheader("🌍 Current Weather Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Districts Selected",
    filtered_latest["district"].nunique(),
)

col2.metric(
    "Average Temperature",
    f"{filtered_latest['temp_c'].mean():.1f} °C",
)

col3.metric(
    "Average Humidity",
    f"{filtered_latest['humidity'].mean():.0f}%",
)

valid_wind = filtered_latest["wind_kph"].dropna()

col4.metric(
    "Average Wind Speed",
    f"{valid_wind.mean():.1f} km/h" if not valid_wind.empty else "N/A",
)


# --------------------------------------------------
# ETL STATUS
# --------------------------------------------------
st.divider()
st.subheader("⚙️ ETL Pipeline & Data Freshness")

last_fetch = df["fetched_at"].max()

if pd.isna(last_fetch):
    st.warning("No fetch timestamp is available.")
else:
    now_utc = pd.Timestamp.now(tz="UTC")
    age_hours = max(
        0.0,
        (now_utc - last_fetch).total_seconds() / 3600,
    )

    status_col1, status_col2, status_col3 = st.columns(3)

    status_col1.metric(
        "Last Database Fetch (UTC)",
        last_fetch.strftime("%Y-%m-%d %H:%M"),
    )

    status_col2.metric(
        "Data Age",
        f"{age_hours:.1f} hours",
    )

    status_col3.metric(
        "Records Stored",
        f"{len(df):,}",
    )

    if age_hours <= 2:
        st.success(
            "Data freshness: Recent data found. "
            "This does not independently confirm the scheduled task succeeded."
        )
    else:
        st.warning(
            "Data may be stale. Check Task Scheduler and run history."
        )

st.caption(
    "Data freshness is based on fetched_at timestamps, "
    "not on the actual Task Scheduler execution result."
)


# --------------------------------------------------
# LATEST TEMPERATURE AND HUMIDITY COMPARISON
# --------------------------------------------------
st.divider()
left, right = st.columns(2)

with left:
    st.subheader("🌡️ Temperature by District")

    temp_df = filtered_latest.dropna(subset=["temp_c"]).sort_values(
        "temp_c", ascending=False
    )

    fig_temp = px.bar(
        temp_df,
        x="district",
        y="temp_c",
        color="temp_c",
        color_continuous_scale="RdYlBu_r",
        labels={
            "district": "District",
            "temp_c": "Temperature (°C)",
        },
    )

    fig_temp.update_layout(
        xaxis_tickangle=-45,
        coloraxis_showscale=False,
        margin=dict(t=20, b=70),
    )

    st.plotly_chart(fig_temp, use_container_width=True)

with right:
    st.subheader("💧 Humidity by District")

    humidity_df = filtered_latest.dropna(
        subset=["humidity"]
    ).sort_values("humidity", ascending=False)

    fig_humidity = px.bar(
        humidity_df,
        x="district",
        y="humidity",
        color="humidity",
        color_continuous_scale="Blues",
        labels={
            "district": "District",
            "humidity": "Humidity (%)",
        },
    )

    fig_humidity.update_layout(
        xaxis_tickangle=-45,
        yaxis_range=[0, 100],
        coloraxis_showscale=False,
        margin=dict(t=20, b=70),
    )

    st.plotly_chart(fig_humidity, use_container_width=True)


# --------------------------------------------------
# HISTORICAL DATA FILTER
# --------------------------------------------------
st.divider()
st.header("📈 Historical Weather Trends")

now_utc = pd.Timestamp.now(tz="UTC")

if period == "Last 24 hours":
    start_time = now_utc - pd.Timedelta(hours=24)
elif period == "Last 7 days":
    start_time = now_utc - pd.Timedelta(days=7)
elif period == "Last 30 days":
    start_time = now_utc - pd.Timedelta(days=30)
else:
    start_time = df["timestamp"].min()

historical = df[
    (df["district"].isin(selected_districts))
    & (df["timestamp"] >= start_time)
    & (df["timestamp"] <= now_utc)
].copy()

if historical.empty:
    st.info(
        "No records found for the selected historical period. "
        "Try another time range or refresh the data."
    )
else:
    st.caption(
        f"Showing {len(historical):,} records from "
        f"{historical['timestamp'].min():%Y-%m-%d %H:%M UTC} "
        f"to {historical['timestamp'].max():%Y-%m-%d %H:%M UTC}"
    )

    # Temperature trend
    st.subheader("🌡️ Temperature Trends")

    temperature_history = historical.dropna(subset=["temp_c"])

    if not temperature_history.empty:
        fig_temp_history = px.line(
            temperature_history,
            x="timestamp",
            y="temp_c",
            color="district",
            markers=True,
            labels={
                "timestamp": "Observation Time (UTC)",
                "temp_c": "Temperature (°C)",
                "district": "District",
            },
        )

        fig_temp_history.update_layout(
            hovermode="x unified",
            margin=dict(t=20, b=20),
            legend_title_text="District",
        )

        st.plotly_chart(
            fig_temp_history,
            use_container_width=True,
        )
    else:
        st.info("No valid temperature measurements for this period.")

    # Humidity trend
    st.subheader("💧 Humidity Trends")

    humidity_history = historical.dropna(subset=["humidity"])

    if not humidity_history.empty:
        fig_humidity_history = px.line(
            humidity_history,
            x="timestamp",
            y="humidity",
            color="district",
            markers=True,
            labels={
                "timestamp": "Observation Time (UTC)",
                "humidity": "Humidity (%)",
                "district": "District",
            },
        )

        fig_humidity_history.update_layout(
            hovermode="x unified",
            yaxis_range=[0, 100],
            margin=dict(t=20, b=20),
            legend_title_text="District",
        )

        st.plotly_chart(
            fig_humidity_history,
            use_container_width=True,
        )
    else:
        st.info("No valid humidity measurements for this period.")

    # District comparison
    st.subheader("📊 Historical District Comparison")

    comparison = (
        historical.groupby("district", as_index=False)
        .agg(
            Average_Temperature=("temp_c", "mean"),
            Average_Humidity=("humidity", "mean"),
            Average_Wind=("wind_kph", "mean"),
            Observation_Count=("timestamp", "count"),
        )
        .sort_values("Average_Temperature", ascending=False)
    )

    comparison_display = comparison.rename(
        columns={
            "district": "District",
            "Average_Temperature": "Avg Temperature (°C)",
            "Average_Humidity": "Avg Humidity (%)",
            "Average_Wind": "Avg Wind (km/h)",
            "Observation_Count": "Observations",
        }
    )

    st.dataframe(
        comparison_display.round(2),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# LATEST WEATHER TABLE
# --------------------------------------------------
st.divider()
st.header("📋 Latest Weather Conditions")

display_df = filtered_latest[
    [
        "district",
        "city",
        "temp_c",
        "humidity",
        "wind_kph",
        "weather_condition",
        "timestamp",
    ]
].copy()

display_df.columns = [
    "District",
    "City",
    "Temperature (°C)",
    "Humidity (%)",
    "Wind (km/h)",
    "Condition",
    "Observation Time (UTC)",
]

display_df["Observation Time (UTC)"] = (
    display_df["Observation Time (UTC)"]
    .dt.strftime("%Y-%m-%d %H:%M")
)

st.dataframe(
    display_df.sort_values(
        "Temperature (°C)", ascending=False
    ),
    use_container_width=True,
    hide_index=True,
)

csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Latest Weather Data (CSV)",
    data=csv_data,
    file_name="sri_lanka_weather_latest.csv",
    mime="text/csv",
)

historical_csv = historical.to_csv(index=False).encode("utf-8") if not historical.empty else b""

st.download_button(
    "⬇️ Download Historical Data (CSV)",
    data=historical_csv,
    file_name="sri_lanka_weather_historical.csv",
    mime="text/csv",
    disabled=historical.empty,
)

st.divider()
st.caption(
    "Source: Open-Meteo API | Database: PostgreSQL | "
    "Dashboard cache: 60 seconds | Times shown in UTC"
)

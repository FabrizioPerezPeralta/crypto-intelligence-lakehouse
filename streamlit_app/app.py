"""
Streamlit Community Cloud Analytics Dashboard:
Connects to MotherDuck SaaS (or local DuckDB fallback) to serve
business intelligence insights processed by dbt.
"""

import os
import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Streamlit Page Config
st.set_page_config(
    page_title="Crypto Market Intelligence Lakehouse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #e9ecef;
    }
    .badge-cloud {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db_connection():
    """Establish cached connection to MotherDuck SaaS or local DuckDB."""
    # Check Streamlit secrets first, then environment variables
    token = None
    if hasattr(st, "secrets") and "MOTHERDUCK_TOKEN" in st.secrets:
        token = st.secrets["MOTHERDUCK_TOKEN"]
    elif os.getenv("MOTHERDUCK_TOKEN"):
        token = os.getenv("MOTHERDUCK_TOKEN")
        
    if token:
        try:
            con = duckdb.connect(f"md:crypto_intelligence?motherduck_token={token}", read_only=True)
            return con, "MotherDuck Cloud (SaaS)"
        except Exception as e:
            st.error(f"❌ Error connecting to MotherDuck Cloud: {e}")
            raise e

    # Fallback to local file (for offline development only)
    local_path = "data/lakehouse.duckdb"
    if not os.path.exists(local_path):
        if os.path.exists("../data/lakehouse.duckdb"):
            local_path = "../data/lakehouse.duckdb"

    if not os.path.exists(local_path):
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        con = duckdb.connect(local_path)
        return con, "Local DuckDB (Empty)"

    con = duckdb.connect(local_path, read_only=True)
    return con, "Local DuckDB Lakehouse"


def load_data(con):
    """Query dimensional model created by dbt."""
    query = """
        SELECT 
            f.coin_id,
            f.coin_symbol,
            d.coin_name,
            d.market_cap_tier,
            f.current_price_usd,
            f.market_cap_usd,
            f.total_volume_24h_usd,
            f.price_change_pct_24h,
            f.intraday_volatility_pct,
            f.ath_drawdown_pct,
            f.volume_to_mcap_ratio,
            f.risk_profile,
            f.snapshot_timestamp
        FROM marts.fct_crypto_market_snapshot f
        JOIN marts.dim_crypto_assets d ON f.coin_id = d.coin_id
        ORDER BY f.market_cap_usd DESC;
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        # Fallback to explicit database catalog namespace if needed
        try:
            return con.execute("""
                SELECT 
                    f.coin_id, f.coin_symbol, d.coin_name, d.market_cap_tier,
                    f.current_price_usd, f.market_cap_usd, f.total_volume_24h_usd,
                    f.price_change_pct_24h, f.intraday_volatility_pct, f.ath_drawdown_pct,
                    f.volume_to_mcap_ratio, f.risk_profile, f.snapshot_timestamp
                FROM crypto_intelligence.marts.fct_crypto_market_snapshot f
                JOIN crypto_intelligence.marts.dim_crypto_assets d ON f.coin_id = d.coin_id
                ORDER BY f.market_cap_usd DESC;
            """).df()
        except Exception:
            raise e


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/dbt-labs/dbt-core/main/core/dbt/include/global_project/dbt.png", width=60)
    st.title("Lakehouse Control")
    
    con, conn_type = get_db_connection()
    st.markdown(f"**Connection:** <span class='badge-cloud'>{conn_type}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🛠️ Architecture Stack")
    st.markdown("""
    * **Orchestration / CI/CD:** GitHub Actions
    * **DWH / Storage:** MotherDuck (Cloud DuckDB)
    * **Transformations:** dbt-duckdb
    * **Serving & UI:** Streamlit Cloud
    * **Cloud Cost:** **$0.00 (100% Free SaaS)**
    """)
    st.markdown("---")
    st.markdown("👨‍💻 **Author:** Fabrizio Perez Peralta")
    st.markdown("📚 *Business Intelligence - Unit II*")


# ---------------- MAIN CONTENT ----------------
st.title("📈 Crypto Market Intelligence & Risk Lakehouse")
st.caption("Automated Data Engineering Solution deployed on MotherDuck Cloud with dbt and GitHub Actions.")

try:
    df = load_data(con)
except Exception as e:
    st.error(f"Error reading marts from Lakehouse: {e}")
    st.info("Run `python scripts/extract_load.py` and `dbt build` to populate the lakehouse.")
    st.stop()

if df.empty:
    st.warning("No data found in the lakehouse marts.")
    st.stop()

# ---------------- KPI BANNER ----------------
col1, col2, col3, col4 = st.columns(4)

total_mcap = df["market_cap_usd"].sum()
total_vol = df["total_volume_24h_usd"].sum()
avg_volatility = df["intraday_volatility_pct"].mean()
top_performer = df.loc[df["price_change_pct_24h"].idxmax()]

with col1:
    st.metric(
        label="Total Tracked Market Cap",
        value=f"${total_mcap / 1e9:.2f} B"
    )

with col2:
    st.metric(
        label="24h Total Volume",
        value=f"${total_vol / 1e9:.2f} B"
    )

with col3:
    st.metric(
        label="Avg Intraday Volatility",
        value=f"{avg_volatility:.2f}%"
    )

with col4:
    st.metric(
        label="Top Performer (24h)",
        value=f"{top_performer['coin_symbol']}",
        delta=f"{top_performer['price_change_pct_24h']:.2f}%"
    )

st.markdown("---")

# ---------------- CHARTS SECTION ----------------
tab1, tab2 = st.tabs(["📊 Market Risk & Volatility Analysis", "🏛️ Capital Distribution"])

with tab1:
    st.subheader("Price Momentum vs. Intraday Volatility Risk")
    
    fig_scatter = px.scatter(
        df,
        x="intraday_volatility_pct",
        y="price_change_pct_24h",
        size="market_cap_usd",
        color="risk_profile",
        hover_name="coin_name",
        hover_data=["coin_symbol", "current_price_usd", "ath_drawdown_pct"],
        color_discrete_map={
            "High Volatility": "#e63946",
            "Moderate Volatility": "#f4a261",
            "Low Volatility / Stable": "#2a9d8f"
        },
        labels={
            "intraday_volatility_pct": "Intraday Volatility (%)",
            "price_change_pct_24h": "24h Price Change (%)",
            "risk_profile": "Risk Profile"
        },
        title="Asset Distribution by Volatility & Price Action (Bubble size = Market Cap)"
    )
    fig_scatter.update_layout(template="plotly_white", height=450)
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.subheader("Market Capitalization by Asset Tier")
    
    tier_summary = df.groupby("market_cap_tier")["market_cap_usd"].sum().reset_index()
    fig_bar = px.bar(
        tier_summary,
        x="market_cap_tier",
        y="market_cap_usd",
        color="market_cap_tier",
        text_auto=".2s",
        labels={"market_cap_usd": "Market Cap (USD)", "market_cap_tier": "Capitalization Tier"},
        title="Total Market Cap Grouped by Asset Tier"
    )
    fig_bar.update_layout(template="plotly_white", height=400, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- MARTS DATA TABLE ----------------
st.markdown("---")
st.subheader("📋 dbt Marts: Curated Fact & Dimension Table")

# Filtering options
selected_tier = st.multiselect(
    "Filter by Market Cap Tier:",
    options=df["market_cap_tier"].unique().tolist(),
    default=df["market_cap_tier"].unique().tolist()
)

filtered_df = df[df["market_cap_tier"].isin(selected_tier)]

# Format columns for display
display_df = filtered_df[[
    "coin_symbol", "coin_name", "market_cap_tier", "current_price_usd",
    "market_cap_usd", "price_change_pct_24h", "intraday_volatility_pct",
    "ath_drawdown_pct", "risk_profile"
]].copy()

display_df.rename(columns={
    "coin_symbol": "Symbol",
    "coin_name": "Asset",
    "market_cap_tier": "Tier",
    "current_price_usd": "Price (USD)",
    "market_cap_usd": "Market Cap",
    "price_change_pct_24h": "24h Change (%)",
    "intraday_volatility_pct": "Volatility (%)",
    "ath_drawdown_pct": "ATH Drawdown (%)",
    "risk_profile": "Risk Category"
}, inplace=True)

st.dataframe(
    display_df.style.format({
        "Price (USD)": "${:,.2f}",
        "Market Cap": "${:,.0f}",
        "24h Change (%)": "{:+.2f}%",
        "Volatility (%)": "{:.2f}%",
        "ATH Drawdown (%)": "{:.2f}%"
    }),
    use_container_width=True,
    height=350
)

# ---------------- FOOTER ----------------
st.markdown("---")
latest_ts = df["snapshot_timestamp"].iloc[0] if "snapshot_timestamp" in df.columns else "N/A"
st.caption(f"🕒 Last data refresh from Lakehouse: **{latest_ts}** | CI/CD Automated via GitHub Actions.")

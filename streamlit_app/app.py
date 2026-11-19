"""
==============================================================================
CRYPTO MARKET INTELLIGENCE LAKEHOUSE — ENTERPRISE BI DASHBOARD
==============================================================================
Orchestration:  GitHub Actions (CI/CD Automated Ingestion & dbt run)
Data Warehouse: MotherDuck SaaS (Cloud DuckDB Lakehouse)
Transform:      dbt-core & dbt-duckdb (Medallion Architecture)
Serving & UI:   Streamlit Community Cloud
Cost:           $0.00 (Zero AWS, 100% Free Public SaaS)
Author:         Fabrizio Perez Peralta (Business Intelligence - Unit II)
==============================================================================
"""

import os
import datetime
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & METADATA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Crypto Market Intelligence Lakehouse",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------------------------------
# 2. ADVANCED PROFESSIONAL CSS STYLING (Fintech Dark/Modern Aesthetic)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Top Header Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(20, 24, 33, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #FFFFFF 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .hero-subtitle {
        font-size: 14px;
        color: #94A3B8;
        font-weight: 400;
    }
    
    /* Status Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pill-green {
        background: rgba(16, 185, 129, 0.12);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .pill-blue {
        background: rgba(59, 130, 246, 0.12);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.25);
    }
    .pill-purple {
        background: rgba(168, 85, 247, 0.12);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.25);
    }
    
    /* Stat Cards */
    .kpi-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 20px 22px;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .kpi-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
        color: #94A3B8;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }
    .kpi-delta-positive {
        font-size: 12px;
        font-weight: 600;
        color: #10B981;
    }
    .kpi-delta-negative {
        font-size: 12px;
        font-weight: 600;
        color: #EF4444;
    }
    
    /* Architecture Badge Container */
    .arch-box {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 10px;
        padding: 12px 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 12px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 3. DATABASE CONNECTION & DATA ACCESS LAYER
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Connecting to MotherDuck Cloud Lakehouse...")
def get_db_connection():
    """Establish cached connection to MotherDuck SaaS or local DuckDB."""
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
            st.error(f"❌ Connection to MotherDuck Cloud failed: {e}")
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
    """Query dimensional model created by dbt, auto-detecting schema namespace."""
    try:
        tables_df = con.execute("""
            SELECT table_catalog, table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'fct_crypto_market_snapshot'
            ORDER BY table_catalog DESC
            LIMIT 1;
        """).df()
    except Exception:
        tables_df = pd.DataFrame()

    if not tables_df.empty:
        cat = tables_df.iloc[0]["table_catalog"]
        sch = tables_df.iloc[0]["table_schema"]
        if cat:
            fct_table = f'"{cat}"."{sch}"."fct_crypto_market_snapshot"'
            dim_table = f'"{cat}"."{sch}"."dim_crypto_assets"'
        else:
            fct_table = f'"{sch}"."fct_crypto_market_snapshot"'
            dim_table = f'"{sch}"."dim_crypto_assets"'
    else:
        fct_table = "marts.fct_crypto_market_snapshot"
        dim_table = "marts.dim_crypto_assets"

    query = f"""
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
        FROM {fct_table} f
        JOIN {dim_table} d ON f.coin_id = d.coin_id
        ORDER BY f.market_cap_usd DESC;
    """
    return con.execute(query).df()


# ----------------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION & PLATFORM CONTROLS
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Lakehouse Platform")
    
    con, conn_type = get_db_connection()
    st.markdown(f"""
    <div style="margin-bottom: 16px;">
        <span class="status-pill pill-green">🟢 {conn_type}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 🔍 Filter & Slice")
    
    search_query = st.text_input("Search Asset", placeholder="e.g. BTC, Solana...", help="Filter by symbol or asset name")
    
    st.markdown("---")
    st.markdown("#### 🏗️ Architecture Stack")
    st.markdown("""
    <div class="arch-box">
        <b>Orchestration:</b> GitHub Actions (Cron 12h)<br>
        <b>Data Warehouse:</b> MotherDuck (Cloud DuckDB)<br>
        <b>Transformations:</b> dbt-core v1.8 (Medallion)<br>
        <b>Serving:</b> Streamlit Community Cloud<br>
        <b>Cloud Spend:</b> <b>$0.00 (Zero AWS)</b>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 🔗 Quick Links")
    st.markdown("""
    * 📂 [GitHub Public Repository](https://github.com/FabrizioPerezPeralta/crypto-intelligence-lakehouse)
    * 🦆 [MotherDuck Cloud Console](https://motherduck.com)
    * 🔶 [dbt Core Documentation](https://docs.getdbt.com)
    """)
    st.markdown("---")
    st.caption("👨‍💻 **Author:** Fabrizio Perez Peralta  \n📚 *Business Intelligence — Unit II*")


# ----------------------------------------------------------------------------
# 5. DATA INGESTION & VALIDATION
# ----------------------------------------------------------------------------
try:
    df = load_data(con)
except Exception as e:
    st.error(f"⚠️ Error querying lakehouse marts: {e}")
    st.info("Execute GitHub Actions workflow or run `python scripts/extract_load.py` and `dbt run`.")
    st.stop()

if df.empty:
    st.warning("⚠️ No data available in the current marts.")
    st.stop()

# Apply search filter if provided
if search_query:
    query_lower = search_query.lower()
    df_filtered = df[
        df["coin_symbol"].str.lower().str.contains(query_lower) |
        df["coin_name"].str.lower().str.contains(query_lower)
    ]
else:
    df_filtered = df.copy()

# ----------------------------------------------------------------------------
# 6. HERO HEADER BANNER
# ----------------------------------------------------------------------------
latest_timestamp = df["snapshot_timestamp"].iloc[0] if "snapshot_timestamp" in df.columns else datetime.datetime.now()

st.markdown(f"""
<div class="hero-container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
            <div class="hero-title">Crypto Market Intelligence Lakehouse</div>
            <div class="hero-subtitle">
                Automated End-to-End Analytics Pipeline • Medallion Data Modeling • Powered by MotherDuck & dbt
            </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <span class="status-pill pill-blue">⚡ dbt Core v1.8</span>
            <span class="status-pill pill-purple">🤖 CI/CD Automated</span>
            <span class="status-pill pill-green">🛡️ 100% Free SaaS</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 7. EXECUTIVE KPI STAT CARDS
# ----------------------------------------------------------------------------
total_mcap = df["market_cap_usd"].sum()
total_vol = df["total_volume_24h_usd"].sum()
avg_volatility = df["intraday_volatility_pct"].mean()
top_gainer = df.loc[df["price_change_pct_24h"].idxmax()]
top_loser = df.loc[df["price_change_pct_24h"].idxmin()]
turnover_ratio = (total_vol / total_mcap) * 100 if total_mcap > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-label">Total Market Cap</span>
            <span>🏛️</span>
        </div>
        <div class="kpi-value">${total_mcap / 1e9:,.2f} B</div>
        <div class="kpi-delta-positive">● {len(df)} Tracked Assets</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-label">24h Aggregate Volume</span>
            <span>📊</span>
        </div>
        <div class="kpi-value">${total_vol / 1e9:,.2f} B</div>
        <div style="font-size: 12px; color: #94A3B8;">Turnover: {turnover_ratio:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-label">Avg Intraday Volatility</span>
            <span>⚡</span>
        </div>
        <div class="kpi-value">{avg_volatility:.2f}%</div>
        <div style="font-size: 12px; color: #F59E0B;">● Market Spread Benchmark</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    gainer_delta = top_gainer['price_change_pct_24h']
    delta_class = "kpi-delta-positive" if gainer_delta >= 0 else "kpi-delta-negative"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-label">Top Performer (24h)</span>
            <span>🚀</span>
        </div>
        <div class="kpi-value">{top_gainer['coin_symbol']}</div>
        <div class="{delta_class}">▲ {gainer_delta:+.2f}% (${top_gainer['current_price_usd']:,.2f})</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 8. ANALYTICS TABS & INTERACTIVE VISUALIZATIONS
# ----------------------------------------------------------------------------
tab_risk, tab_capital, tab_marts, tab_arch = st.tabs([
    "🎯 Risk & Volatility Matrix",
    "📊 Capital Distribution & Dominance",
    "📋 Curated dbt Data Marts",
    "🏗️ Pipeline Architecture & Lineage"
])

# ---- TAB 1: RISK & VOLATILITY MATRIX ----
with tab_risk:
    st.markdown("#### Asset Volatility Risk vs. 24h Price Action")
    st.caption("Quadrant Analysis: Identifies over-leveraged, high-volatility momentum assets versus stable stores of value.")
    
    # Plotly Scatter Plot (Risk vs Return)
    fig_scatter = px.scatter(
        df_filtered,
        x="intraday_volatility_pct",
        y="price_change_pct_24h",
        size="market_cap_usd",
        color="risk_profile",
        hover_name="coin_name",
        hover_data={
            "coin_symbol": True,
            "current_price_usd": ":$,.2f",
            "market_cap_usd": ":$,.0f",
            "ath_drawdown_pct": ":.2f%"
        },
        color_discrete_map={
            "High Volatility": "#EF4444",
            "Moderate Volatility": "#F59E0B",
            "Low Volatility / Stable": "#10B981"
        },
        labels={
            "intraday_volatility_pct": "Intraday Volatility Spread (%)",
            "price_change_pct_24h": "24h Price Change (%)",
            "risk_profile": "Risk Classification"
        }
    )
    
    # Reference Benchmark Lines
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="rgba(255, 255, 255, 0.25)", annotation_text="Break-even", annotation_position="bottom right")
    fig_scatter.add_vline(x=avg_volatility, line_dash="dot", line_color="rgba(245, 158, 11, 0.4)", annotation_text="Market Avg Volatility", annotation_position="top left")
    
    fig_scatter.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        height=480,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Top Gainers vs Top Losers Bar Chart
    col_gain, col_lose = st.columns(2)
    
    top_5_gainers = df.sort_values(by="price_change_pct_24h", ascending=False).head(5)
    top_5_losers = df.sort_values(by="price_change_pct_24h", ascending=True).head(5)
    
    with col_gain:
        st.markdown("##### 🟢 Top 5 Market Leaders (24h)")
        fig_gain = px.bar(
            top_5_gainers,
            x="price_change_pct_24h",
            y="coin_symbol",
            orientation="h",
            color="price_change_pct_24h",
            color_continuous_scale=["#059669", "#10B981"],
            text_auto="+.2f",
            labels={"price_change_pct_24h": "Gain (%)", "coin_symbol": "Asset"}
        )
        fig_gain.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=260, coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_gain, use_container_width=True)

    with col_lose:
        st.markdown("##### 🔴 Bottom 5 Market Laggards (24h)")
        fig_lose = px.bar(
            top_5_losers,
            x="price_change_pct_24h",
            y="coin_symbol",
            orientation="h",
            color="price_change_pct_24h",
            color_continuous_scale=["#DC2626", "#EF4444"],
            text_auto="+.2f",
            labels={"price_change_pct_24h": "Loss (%)", "coin_symbol": "Asset"}
        )
        fig_lose.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=260, coloraxis_showscale=False, yaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_lose, use_container_width=True)


# ---- TAB 2: CAPITAL DISTRIBUTION ----
with tab_capital:
    st.markdown("#### Market Capitalization Dominance & Liquidity Turnover")
    
    col_tree, col_liq = st.columns([3, 2])
    
    with col_tree:
        st.markdown("##### 🏛️ Capital Distribution Treemap")
        fig_tree = px.treemap(
            df_filtered,
            path=["market_cap_tier", "coin_symbol"],
            values="market_cap_usd",
            color="price_change_pct_24h",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            hover_data=["coin_name", "current_price_usd"]
        )
        fig_tree.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=450)
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_liq:
        st.markdown("##### 💧 Liquidity Turnover (Volume / Market Cap)")
        st.caption("Higher ratio signifies higher trading interest relative to circulating market size.")
        fig_liq = px.bar(
            df_filtered.sort_values(by="volume_to_mcap_ratio", ascending=False).head(8),
            x="volume_to_mcap_ratio",
            y="coin_symbol",
            orientation="h",
            color="volume_to_mcap_ratio",
            color_continuous_scale="Viridis",
            labels={"volume_to_mcap_ratio": "Volume/MCap Ratio", "coin_symbol": "Asset"}
        )
        fig_liq.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_liq, use_container_width=True)


# ---- TAB 3: CURATED DBT DATA MARTS ----
with tab_marts:
    st.markdown("#### 📋 Star Schema Marts (`fct_crypto_market_snapshot` ⨝ `dim_crypto_assets`)")
    st.caption("Cleaned, deduplicated, and business-ready data output generated by dbt models.")

    # Tier Multiselect Filter
    tier_options = df["market_cap_tier"].unique().tolist()
    selected_tiers = st.multiselect("Filter by Capitalization Tier", options=tier_options, default=tier_options)
    
    view_df = df_filtered[df_filtered["market_cap_tier"].isin(selected_tiers)].copy()

    # Formatted display columns
    display_table = view_df[[
        "coin_symbol", "coin_name", "market_cap_tier", "current_price_usd",
        "market_cap_usd", "total_volume_24h_usd", "price_change_pct_24h",
        "intraday_volatility_pct", "ath_drawdown_pct", "risk_profile"
    ]].rename(columns={
        "coin_symbol": "Symbol",
        "coin_name": "Asset Name",
        "market_cap_tier": "Tier",
        "current_price_usd": "Price (USD)",
        "market_cap_usd": "Market Cap",
        "total_volume_24h_usd": "24h Volume",
        "price_change_pct_24h": "24h Change (%)",
        "intraday_volatility_pct": "Volatility (%)",
        "ath_drawdown_pct": "ATH Drawdown (%)",
        "risk_profile": "Risk Category"
    })

    st.dataframe(
        display_table.style.format({
            "Price (USD)": "${:,.2f}",
            "Market Cap": "${:,.0f}",
            "24h Volume": "${:,.0f}",
            "24h Change (%)": "{:+.2f}%",
            "Volatility (%)": "{:.2f}%",
            "ATH Drawdown (%)": "{:.2f}%"
        }),
        use_container_width=True,
        height=400
    )

    # Download Marts CSV
    csv_data = view_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Marts to CSV",
        data=csv_data,
        file_name=f"crypto_marts_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )


# ---- TAB 4: ARCHITECTURE & LINEAGE ----
with tab_arch:
    st.markdown("#### 🏗️ Medallion Architecture & Automated CI/CD Lineage")
    st.markdown("""
    This Data Platform implements a modern **Medallion Architecture** to guarantee data governance and quality assurance:
    """)
    
    col_b, col_s, col_g = st.columns(3)
    
    with col_b:
        st.markdown("""
        <div class="kpi-card">
            <h4 style="color: #CD7F32; margin-top: 0;">🥉 Bronze (Raw Layer)</h4>
            <p style="font-size: 13px; color: #94A3B8;">
                <b>Target:</b> <code>raw.raw_crypto_market</code><br>
                <b>Ingestion:</b> Python EL script querying public financial API.<br>
                <b>Schema:</b> Immutable append-only batches with ingestion timestamps.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_s:
        st.markdown("""
        <div class="kpi-card">
            <h4 style="color: #C0C0C0; margin-top: 0;">🥈 Silver (Intermediate Layer)</h4>
            <p style="font-size: 13px; color: #94A3B8;">
                <b>Models:</b> <code>stg_crypto_market</code> & <code>int_crypto_volatility_metrics</code><br>
                <b>Transforms:</b> Window deduplication, intraday spread calculation, capitalization tiers.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_g:
        st.markdown("""
        <div class="kpi-card">
            <h4 style="color: #FFD700; margin-top: 0;">🥇 Gold (Business Marts)</h4>
            <p style="font-size: 13px; color: #94A3B8;">
                <b>Models:</b> <code>fct_crypto_market_snapshot</code> & <code>dim_crypto_assets</code><br>
                <b>Format:</b> Dimensional Star Schema validated via <code>dbt test</code> for zero NULLs and referential integrity.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 🧪 Automated CI/CD Quality Controls (`dbt test`)")
    st.markdown("""
    Every time code is pushed or triggered by the automated 12-hour cron schedule, GitHub Actions validates:
    * `not_null` assertions on all primary keys (`coin_id`, `coin_symbol`, `current_price_usd`).
    * `unique` assertions guaranteeing zero duplicate dimension entities.
    * `relationships` tests enforcing foreign key constraints between facts and dimensions.
    * `accepted_values` testing risk categories (`High Volatility`, `Moderate Volatility`, `Low Volatility / Stable`).
    """)

# ----------------------------------------------------------------------------
# 9. FOOTER
# ----------------------------------------------------------------------------
st.markdown("---")
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; color: #64748B; font-size: 12px; flex-wrap: wrap;">
    <div>🕒 <b>Last Data Synchronization:</b> {latest_timestamp}</div>
    <div>⚡ Built with <b>MotherDuck</b>, <b>dbt-duckdb</b>, <b>Streamlit</b> & <b>GitHub Actions</b></div>
</div>
""", unsafe_allow_html=True)

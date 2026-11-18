with metrics as (
    select * from {{ ref('int_crypto_volatility_metrics') }}
)

select
    coin_id,
    coin_symbol,
    current_price_usd,
    market_cap_usd,
    total_volume_24h_usd,
    high_24h_usd,
    low_24h_usd,
    price_change_pct_24h,
    price_spread_24h_usd,
    intraday_volatility_pct,
    ath_drawdown_pct,
    volume_to_mcap_ratio,
    
    -- Risk Profile Classification for Business Intelligence
    case
        when intraday_volatility_pct >= 6.0 or abs(price_change_pct_24h) >= 8.0 then 'High Volatility'
        when intraday_volatility_pct >= 2.5 or abs(price_change_pct_24h) >= 3.0 then 'Moderate Volatility'
        else 'Low Volatility / Stable'
    end as risk_profile,
    
    ingested_at as snapshot_timestamp

from metrics

with staging as (
    select * from {{ ref('stg_crypto_market') }}
),

metrics_calculated as (
    select
        coin_id,
        coin_symbol,
        coin_name,
        current_price_usd,
        market_cap_usd,
        total_volume_24h_usd,
        high_24h_usd,
        low_24h_usd,
        price_change_pct_24h,
        all_time_high_usd,
        circulating_supply,
        ingested_at,
        
        -- Price spread in 24 hours
        round(high_24h_usd - low_24h_usd, 4) as price_spread_24h_usd,
        
        -- Intraday Volatility %: (High - Low) / Low * 100
        round(
            ((high_24h_usd - low_24h_usd) / nullif(low_24h_usd, 0)) * 100, 
            2
        ) as intraday_volatility_pct,
        
        -- Drawdown from All-Time High %: (Current - ATH) / ATH * 100
        round(
            ((current_price_usd - all_time_high_usd) / nullif(all_time_high_usd, 0)) * 100, 
            2
        ) as ath_drawdown_pct,
        
        -- Liquidity turnover indicator: Volume / Market Cap
        round(
            total_volume_24h_usd / nullif(market_cap_usd, 0), 
            4
        ) as volume_to_mcap_ratio,
        
        -- Market Capitalization Tier Classification
        case 
            when market_cap_usd >= 100000000000 then 'Mega Cap (>100B)'
            when market_cap_usd >= 10000000000 then 'Large Cap (10B - 100B)'
            when market_cap_usd >= 1000000000 then 'Mid Cap (1B - 10B)'
            else 'Small Cap (<1B)'
        end as market_cap_tier

    from staging
)

select * from metrics_calculated

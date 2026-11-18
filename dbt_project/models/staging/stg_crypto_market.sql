with source_data as (
    select * from raw.raw_crypto_market
),

deduplicated as (
    select
        id as coin_id,
        upper(trim(symbol)) as coin_symbol,
        trim(name) as coin_name,
        cast(current_price as double) as current_price_usd,
        cast(market_cap as double) as market_cap_usd,
        cast(total_volume as double) as total_volume_24h_usd,
        cast(high_24h as double) as high_24h_usd,
        cast(low_24h as double) as low_24h_usd,
        cast(price_change_percentage_24h as double) as price_change_pct_24h,
        cast(ath as double) as all_time_high_usd,
        cast(circulating_supply as double) as circulating_supply,
        cast(ingestion_timestamp as timestamp) as ingested_at,
        row_number() over (
            partition by id 
            order by ingestion_timestamp desc
        ) as row_num
    from source_data
)

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
    ingested_at
from deduplicated
where row_num = 1

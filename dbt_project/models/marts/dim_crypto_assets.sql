with intermediate as (
    select * from {{ ref('int_crypto_volatility_metrics') }}
)

select
    coin_id,
    coin_symbol,
    coin_name,
    market_cap_tier,
    circulating_supply,
    all_time_high_usd,
    ingested_at as first_seen_at
from intermediate

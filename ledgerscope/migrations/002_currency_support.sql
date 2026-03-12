-- Migration 002: Add multi-currency support
-- This migration adds exchange rate tracking and currency fields

-- Create exchange_rates table for storing historical exchange rates
CREATE TABLE IF NOT EXISTS exchange_rates (
    date DATE NOT NULL,
    from_currency VARCHAR NOT NULL,
    to_currency VARCHAR NOT NULL,
    rate DOUBLE NOT NULL,
    source VARCHAR DEFAULT 'manual',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, from_currency, to_currency)
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_exchange_rates_lookup 
ON exchange_rates(from_currency, to_currency, date);

-- Add index for date range queries
CREATE INDEX IF NOT EXISTS idx_exchange_rates_date 
ON exchange_rates(date);

-- Create view for latest exchange rates
CREATE OR REPLACE VIEW latest_exchange_rates AS
SELECT 
    from_currency,
    to_currency,
    rate,
    date,
    source
FROM exchange_rates
WHERE (from_currency, to_currency, date) IN (
    SELECT from_currency, to_currency, MAX(date) as date
    FROM exchange_rates
    GROUP BY from_currency, to_currency
);

-- Create view for portfolio values in base currency
CREATE OR REPLACE VIEW holdings_base_currency AS
WITH latest_prices AS (
    SELECT 
        symbol,
        MAX(date) as latest_date
    FROM prices
    GROUP BY symbol
),
current_prices AS (
    SELECT 
        p.symbol,
        p.close as current_price,
        p.date
    FROM prices p
    JOIN latest_prices lp ON p.symbol = lp.symbol AND p.date = lp.latest_date
)
SELECT 
    h.symbol,
    h.shares,
    h.avg_cost,
    cp.current_price,
    t.currency,
    h.shares * cp.current_price as market_value_original_currency,
    COALESCE(
        h.shares * cp.current_price * er.rate,
        h.shares * cp.current_price
    ) as market_value_base_currency,
    COALESCE(er.rate, 1.0) as exchange_rate,
    COALESCE(er.to_currency, t.currency) as base_currency
FROM holdings h
LEFT JOIN current_prices cp ON h.symbol = cp.symbol
LEFT JOIN transactions t ON h.symbol = t.symbol
LEFT JOIN latest_exchange_rates er 
    ON t.currency = er.from_currency
WHERE h.shares > 0
GROUP BY h.symbol, h.shares, h.avg_cost, cp.current_price, t.currency, er.rate, er.to_currency;

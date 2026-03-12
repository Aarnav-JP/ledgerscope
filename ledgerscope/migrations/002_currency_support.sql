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

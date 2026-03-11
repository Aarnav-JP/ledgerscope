-- LedgerScope initial schema
-- Creates core tables: transactions, prices, macro_data

CREATE TABLE IF NOT EXISTS transactions (
    id              VARCHAR PRIMARY KEY,
    broker          VARCHAR NOT NULL,
    trade_date      DATE NOT NULL,
    settle_date     DATE,
    symbol          VARCHAR NOT NULL,
    isin            VARCHAR,
    action          VARCHAR NOT NULL,  -- BUY, SELL, DIVIDEND, SPLIT
    quantity        DOUBLE NOT NULL,
    price           DOUBLE NOT NULL,
    fees            DOUBLE DEFAULT 0,
    currency        VARCHAR DEFAULT 'USD',
    exchange        VARCHAR,
    notes           VARCHAR,
    imported_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prices (
    symbol      VARCHAR NOT NULL,
    date        DATE NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE NOT NULL,
    adj_close   DOUBLE,
    volume      BIGINT,
    source      VARCHAR DEFAULT 'yfinance',
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS macro_data (
    series_id   VARCHAR NOT NULL,
    date        DATE NOT NULL,
    value       DOUBLE,
    series_name VARCHAR,
    PRIMARY KEY (series_id, date)
);

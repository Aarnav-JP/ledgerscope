-- ============================================================
-- LedgerScope Analytics Views
-- All risk metrics and P&L figures as composable SQL views
-- ============================================================

-- VIEW: holdings
-- Current portfolio positions: what you own and what you paid
CREATE OR REPLACE VIEW holdings AS
SELECT
    symbol,
    SUM(CASE WHEN action = 'BUY' THEN quantity ELSE 0 END)
    - SUM(CASE WHEN action = 'SELL' THEN quantity ELSE 0 END) AS shares,
    SUM(CASE WHEN action = 'BUY' THEN (quantity * price + fees) ELSE 0 END)
    / NULLIF(SUM(CASE WHEN action = 'BUY' THEN quantity ELSE 0 END), 0) AS avg_cost,
    MAX(trade_date) AS last_trade_date
FROM transactions
WHERE action IN ('BUY', 'SELL')
GROUP BY symbol
HAVING
    SUM(CASE WHEN action = 'BUY' THEN quantity ELSE 0 END)
    - SUM(CASE WHEN action = 'SELL' THEN quantity ELSE 0 END) > 0;


-- VIEW: risk_summary
-- Key risk metrics per holding: Sharpe, volatility, worst day, annual return
CREATE OR REPLACE VIEW risk_summary AS
WITH daily_returns AS (
    SELECT
        p.symbol,
        p.date,
        (p.adj_close - LAG(p.adj_close) OVER (PARTITION BY p.symbol ORDER BY p.date))
        / NULLIF(LAG(p.adj_close) OVER (PARTITION BY p.symbol ORDER BY p.date), 0) AS ret
    FROM prices p
    WHERE p.symbol IN (SELECT symbol FROM holdings)
),
stats AS (
    SELECT
        symbol,
        AVG(ret) AS mean_return,
        STDDEV(ret) AS volatility,
        AVG(ret) / NULLIF(STDDEV(ret), 0) * SQRT(252) AS sharpe,
        MIN(ret) AS worst_day,
        COUNT(*) AS trading_days
    FROM daily_returns
    WHERE ret IS NOT NULL
    GROUP BY symbol
)
SELECT
    h.symbol,
    h.shares,
    h.avg_cost,
    ROUND(s.sharpe, 4) AS sharpe,
    ROUND(s.volatility * SQRT(252), 4) AS annual_vol,
    ROUND(s.worst_day, 4) AS worst_day,
    ROUND(s.mean_return * 252, 4) AS annual_return,
    s.trading_days
FROM holdings h
LEFT JOIN stats s ON h.symbol = s.symbol;


-- VIEW: pnl_history
-- Daily unrealized P&L per symbol over time
CREATE OR REPLACE VIEW pnl_history AS
WITH position_at_date AS (
    SELECT
        t.symbol,
        p.date,
        SUM(CASE
            WHEN t.action = 'BUY' AND t.trade_date <= p.date THEN t.quantity
            WHEN t.action = 'SELL' AND t.trade_date <= p.date THEN -t.quantity
            ELSE 0
        END) AS cumulative_shares,
        SUM(CASE
            WHEN t.action = 'BUY' AND t.trade_date <= p.date THEN t.quantity * t.price + t.fees
            ELSE 0
        END) AS cumulative_cost,
        SUM(CASE
            WHEN t.action = 'SELL' AND t.trade_date <= p.date THEN t.quantity * (t.price - (
                SELECT SUM(t2.quantity * t2.price + t2.fees) / NULLIF(SUM(t2.quantity), 0)
                FROM transactions t2
                WHERE t2.symbol = t.symbol AND t2.action = 'BUY' AND t2.trade_date <= t.trade_date
            ))
            ELSE 0
        END) AS cumulative_realized
    FROM transactions t
    JOIN prices p ON t.symbol = p.symbol
    WHERE t.action IN ('BUY', 'SELL')
    GROUP BY t.symbol, p.date
)
SELECT
    pad.symbol,
    pad.date,
    p.close AS current_price,
    pad.cumulative_shares AS shares,
    pad.cumulative_cost AS cost_basis,
    ROUND(pad.cumulative_shares * p.close - pad.cumulative_cost, 2) AS unrealized_pnl,
    ROUND(pad.cumulative_realized, 2) AS realized_pnl,
    ROUND(pad.cumulative_shares * p.close, 2) AS market_value
FROM position_at_date pad
JOIN prices p ON pad.symbol = p.symbol AND pad.date = p.date
WHERE pad.cumulative_shares > 0;


-- VIEW: drawdown
-- Maximum drawdown per symbol
CREATE OR REPLACE VIEW drawdown AS
WITH running_values AS (
    SELECT
        symbol,
        date,
        adj_close,
        MAX(adj_close) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_max
    FROM prices
    WHERE symbol IN (SELECT symbol FROM holdings)
),
drawdown_series AS (
    SELECT
        symbol,
        date,
        adj_close,
        running_max,
        (adj_close - running_max) / NULLIF(running_max, 0) AS drawdown_pct
    FROM running_values
)
SELECT
    symbol,
    ROUND(MIN(drawdown_pct), 4) AS max_drawdown,
    (SELECT date FROM drawdown_series ds2
     WHERE ds2.symbol = drawdown_series.symbol
     ORDER BY drawdown_pct ASC LIMIT 1) AS max_drawdown_date
FROM drawdown_series
GROUP BY symbol;


-- VIEW: benchmark_comparison
-- Portfolio vs benchmark (SPY) performance metrics
CREATE OR REPLACE VIEW benchmark_comparison AS
WITH portfolio_returns AS (
    SELECT
        p.date,
        p.symbol,
        (p.adj_close - LAG(p.adj_close) OVER (PARTITION BY p.symbol ORDER BY p.date))
        / NULLIF(LAG(p.adj_close) OVER (PARTITION BY p.symbol ORDER BY p.date), 0) AS port_ret
    FROM prices p
    WHERE p.symbol IN (SELECT symbol FROM holdings)
),
benchmark_returns AS (
    SELECT
        date,
        (adj_close - LAG(adj_close) OVER (ORDER BY date))
        / NULLIF(LAG(adj_close) OVER (ORDER BY date), 0) AS bench_ret
    FROM prices
    WHERE symbol = 'SPY'
),
paired AS (
    SELECT
        pr.symbol,
        pr.date,
        pr.port_ret,
        br.bench_ret
    FROM portfolio_returns pr
    JOIN benchmark_returns br ON pr.date = br.date
    WHERE pr.port_ret IS NOT NULL AND br.bench_ret IS NOT NULL
)
SELECT
    symbol,
    ROUND(CORR(port_ret, bench_ret), 4) AS correlation,
    ROUND(
        COVAR_POP(port_ret, bench_ret) / NULLIF(VAR_POP(bench_ret), 0),
        4
    ) AS beta,
    ROUND(
        AVG(port_ret) * 252 -
        (COVAR_POP(port_ret, bench_ret) / NULLIF(VAR_POP(bench_ret), 0)) * AVG(bench_ret) * 252,
        4
    ) AS alpha,
    COUNT(*) AS common_days
FROM paired
GROUP BY symbol;


-- VIEW: dividend_income
-- Dividend aggregations and yield on cost
CREATE OR REPLACE VIEW dividend_income AS
WITH dividends AS (
    SELECT
        symbol,
        EXTRACT(YEAR FROM trade_date) AS year,
        SUM(quantity * price) AS annual_dividend
    FROM transactions
    WHERE action = 'DIVIDEND'
    GROUP BY symbol, EXTRACT(YEAR FROM trade_date)
)
SELECT
    d.symbol,
    d.year,
    ROUND(d.annual_dividend, 2) AS annual_dividend,
    ROUND(SUM(d.annual_dividend) OVER (
        PARTITION BY d.symbol ORDER BY d.year
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS cumulative_dividend,
    ROUND(
        d.annual_dividend / NULLIF(h.avg_cost * h.shares, 0) * 100,
        2
    ) AS yield_on_cost_pct
FROM dividends d
LEFT JOIN holdings h ON d.symbol = h.symbol
ORDER BY d.symbol, d.year;


-- ============================================================
-- Multi-Currency Support Views
-- ============================================================

-- VIEW: latest_exchange_rates
-- Most recent exchange rate for each currency pair
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


-- VIEW: holdings_base_currency
-- Portfolio holdings with values converted to base currency
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


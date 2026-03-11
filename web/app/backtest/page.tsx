"use client";

import { useState } from 'react';
import { runBacktest } from '@/lib/api';
import MetricCard from '@/components/MetricCard';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function BacktestPage() {
  const [strategy, setStrategy] = useState("SELECT date, 'RELIANCE' as symbol,\n  CASE WHEN close > AVG(close) OVER (ORDER BY date ROWS 19 PRECEDING) THEN 'BUY' ELSE 'SELL' END as signal\nFROM prices WHERE symbol = 'RELIANCE'");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest(strategy, symbol, startDate);
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <h1 className="section-heading font-sans text-2xl font-semibold text-[var(--text)] mb-8">
        Strategy Backtester
      </h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        {/* Strategy Input Panel */}
        <div className="lg:col-span-1 glass-card p-6 h-fit">
          <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--text-muted)] mb-5">Configuration</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-2">Symbol</label>
              <input 
                type="text" 
                value={symbol} 
                onChange={(e) => setSymbol(e.target.value)}
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-2">Start Date</label>
              <input 
                type="date" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)}
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] block mb-2">Strategy SQL</label>
              <textarea 
                value={strategy} 
                onChange={(e) => setStrategy(e.target.value)}
                className="input-field h-48 resize-y text-xs leading-relaxed"
                required
              />
            </div>
            <button 
              type="submit" 
              disabled={loading}
              className="btn-accent"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-[var(--bg)] border-t-transparent rounded-full animate-spin" />
                  Running...
                </span>
              ) : "Run Backtest"}
            </button>
          </form>
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-[var(--negative-dim)] border border-[var(--negative)]">
              <p className="text-[var(--negative)] font-mono text-xs">{error}</p>
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2">
          {result && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                <MetricCard 
                  label="Total Return" 
                  value={`${result.total_return_pct >= 0 ? '+' : ''}${result.total_return_pct.toFixed(2)}%`}
                  positive={result.total_return_pct >= 0}
                />
                <MetricCard 
                  label="Ann. Return" 
                  value={`${result.annualized_return_pct >= 0 ? '+' : ''}${result.annualized_return_pct.toFixed(2)}%`}
                  positive={result.annualized_return_pct >= 0}
                />
                <MetricCard label="Sharpe" value={result.sharpe_ratio ? result.sharpe_ratio.toFixed(4) : "N/A"} positive={result.sharpe_ratio >= 0} />
                <MetricCard label="Max Drawdown" value={`${result.max_drawdown_pct.toFixed(2)}%`} positive={false} />
                <MetricCard label="Win Rate" value={`${result.win_rate_pct.toFixed(1)}%`} positive={null} />
                <MetricCard label="Trades" value={result.num_trades} positive={null} />
                <MetricCard label="Final Equity" value={`$${result.final_value.toLocaleString(undefined, {minimumFractionDigits: 2})}`} positive={result.final_value >= result.initial_capital} />
              </div>

              <div className="glass-card p-6">
                <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--text-muted)] mb-5">Equity Curve</h2>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={result.equity_curve}>
                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
                          <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="var(--text-muted)" 
                        fontSize={11} 
                        fontFamily="var(--font-ibm-mono)"
                        tickLine={false} 
                        axisLine={false} 
                      />
                      <YAxis 
                        stroke="var(--text-muted)" 
                        fontSize={11} 
                        fontFamily="var(--font-ibm-mono)"
                        tickLine={false} 
                        axisLine={false} 
                        tickFormatter={(val) => `$${val.toLocaleString()}`}
                        domain={['auto', 'auto']}
                        width={80}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'var(--surface2)', 
                          border: '1px solid var(--border-bright)', 
                          borderRadius: '8px',
                          color: 'var(--text)',
                          fontFamily: 'var(--font-ibm-mono)',
                          fontSize: '12px',
                          boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
                        }}
                        formatter={(value: any) => [`$${Number(value).toLocaleString(undefined, {minimumFractionDigits: 2})}`, 'Equity']}
                      />
                      <Area type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={2} fill="url(#equityGrad)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
          {!result && !loading && (
            <div className="glass-card flex items-center justify-center h-[400px]">
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[var(--accent-dim)] flex items-center justify-center">
                  <span className="text-[var(--accent)] text-xl">▶</span>
                </div>
                <p className="text-[var(--text-dim)] font-sans text-sm">Submit a strategy to see results</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

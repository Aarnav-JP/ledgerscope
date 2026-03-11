"use client";

import { useState } from 'react';
import { runBacktest } from '@/lib/api';
import MetricCard from '@/components/MetricCard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

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
      <h1 className="text-2xl text-accent font-serif italic mb-6">Strategy Backtester</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
        <div className="md:col-span-1 bg-surface border border-border p-6 rounded-none h-fit">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="font-mono text-xs uppercase text-text-dim block mb-2">Symbol</label>
              <input 
                type="text" 
                value={symbol} 
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full bg-surface2 border border-border p-2 focus:border-accent text-text font-mono"
                required
              />
            </div>
            <div>
              <label className="font-mono text-xs uppercase text-text-dim block mb-2">Start Date</label>
              <input 
                type="date" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-surface2 border border-border p-2 focus:border-accent text-text font-mono"
                required
              />
            </div>
            <div>
              <label className="font-mono text-xs uppercase text-text-dim block mb-2">Condition (SQL)</label>
              <textarea 
                value={strategy} 
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full h-48 bg-surface2 border border-border p-2 focus:border-accent text-text font-mono text-sm leading-relaxed"
                required
              />
            </div>
            <button 
              type="submit" 
              disabled={loading}
              className="bg-accent text-bg font-sans font-semibold py-2 px-4 hover:bg-opacity-80 transition-opacity disabled:opacity-50"
            >
              {loading ? "Running..." : "Run Backtest"}
            </button>
          </form>
          {error && <div className="mt-4 text-negative font-mono text-sm">{error}</div>}
        </div>

        <div className="md:col-span-2">
          {result && (
            <>
              <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
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
                <MetricCard label="Sharpe Ratio" value={result.sharpe_ratio ? result.sharpe_ratio.toFixed(4) : "N/A"} positive={result.sharpe_ratio >= 0} />
                <MetricCard label="Max Drawdown" value={`${result.max_drawdown_pct.toFixed(2)}%`} positive={false} />
                <MetricCard label="Win Rate" value={`${result.win_rate_pct.toFixed(1)}%`} positive={null} />
                <MetricCard label="Total Trades" value={result.num_trades} positive={null} />
                <MetricCard label="Final Equity" value={`$${result.final_value.toLocaleString(undefined, {minimumFractionDigits: 2})}`} positive={result.final_value >= result.initial_capital} />
              </div>

              <div className="bg-surface border border-border p-6 h-80">
                <h2 className="text-lg font-mono text-text-dim uppercase mb-4">Equity Curve</h2>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.equity_curve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val.toLocaleString()}`} domain={['auto', 'auto']} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
                      itemStyle={{ color: 'var(--accent)' }}
                      formatter={(value: any) => [`$${Number(value).toLocaleString(undefined, {minimumFractionDigits: 2})}`, 'Equity']}
                    />
                    <Line type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
          {!result && !loading && (
            <div className="text-text-dim text-center h-full flex items-center justify-center border border-dashed border-border">
              Submit a strategy to see results
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

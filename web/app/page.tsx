"use client";

import { useEffect, useState } from 'react';
import { fetchSummary, fetchPnL, fetchHoldings } from '@/lib/api';
import MetricCard from '@/components/MetricCard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function OverviewPage() {
  const [summary, setSummary] = useState<any>(null);
  const [pnl, setPnL] = useState<any[]>([]);
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sumData, pnlData, holdData] = await Promise.all([
          fetchSummary(),
          fetchPnL(),
          fetchHoldings()
        ]);
        setSummary(sumData);
        setHoldings(holdData);
        
        // Aggregate PnL by date for the portfolio value chart
        const valueByDate: Record<string, number> = {};
        pnlData.forEach((record: any) => {
          if (!valueByDate[record.date]) valueByDate[record.date] = 0;
          valueByDate[record.date] += record.market_value;
        });
        
        const chartData = Object.keys(valueByDate).sort().map(date => ({
          date,
          value: valueByDate[date]
        }));
        
        setPnL(chartData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="text-text-dim mt-10 text-center animate-pulse">Loading overview...</div>;
  if (!summary) return <div className="text-negative mt-10">Error loading data. Is the backend running?</div>;

  return (
    <main>
      <h1 className="text-2xl text-accent font-serif italic mb-6">Portfolio Overview</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <MetricCard 
          label="Total Value" 
          value={`$${summary.total_value.toLocaleString(undefined, {minimumFractionDigits: 2})}`} 
          positive={null} 
        />
        <MetricCard 
          label="Total Cost Basis" 
          value={`$${summary.total_cost.toLocaleString(undefined, {minimumFractionDigits: 2})}`} 
          positive={null} 
        />
        <MetricCard 
          label="Total P&L" 
          value={`$${summary.total_pnl.toLocaleString(undefined, {minimumFractionDigits: 2})}`} 
          delta={`${summary.total_pnl_pct >= 0 ? '+' : ''}${summary.total_pnl_pct.toFixed(2)}%`}
          positive={summary.total_pnl >= 0} 
        />
        <MetricCard 
          label="Portfolio Sharpe" 
          value={summary.portfolio_sharpe !== null ? summary.portfolio_sharpe.toFixed(4) : "N/A"} 
          positive={summary.portfolio_sharpe >= 0} 
        />
      </div>

      <div className="bg-surface border border-border p-6 mb-8 h-96">
        <h2 className="text-lg font-mono text-text-dim uppercase mb-4">Portfolio Value Over Time</h2>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={pnl}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val.toLocaleString()}`} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
              itemStyle={{ color: 'var(--accent)' }}
              formatter={(value: number) => [`$${value.toLocaleString(undefined, {minimumFractionDigits: 2})}`, 'Value']}
            />
            <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <h2 className="text-lg font-mono text-text-dim uppercase mb-4">Top Holdings</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim">Symbol</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Shares</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Avg Cost</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Last Trade</th>
            </tr>
          </thead>
          <tbody>
            {holdings.slice(0, 5).map((h, i) => (
              <tr key={h.symbol} className={i % 2 === 0 ? "bg-surface" : "bg-surface2"}>
                <td className="border border-border p-3 font-mono">{h.symbol}</td>
                <td className="border border-border p-3 font-mono text-right">{h.shares.toFixed(4)}</td>
                <td className="border border-border p-3 font-mono text-right">${h.avg_cost.toFixed(2)}</td>
                <td className="border border-border p-3 font-mono text-right">{h.last_trade_date}</td>
              </tr>
            ))}
            {holdings.length === 0 && (
              <tr>
                <td colSpan={4} className="border border-border p-3 text-center text-text-dim">No holdings found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

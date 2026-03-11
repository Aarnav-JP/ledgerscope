"use client";

import { useEffect, useState } from 'react';
import { fetchSummary, fetchPnL, fetchHoldings } from '@/lib/api';
import MetricCard from '@/components/MetricCard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts';

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
        
        // Aggregate market value by date, tracking symbol count per date
        const valueByDate: Record<string, number> = {};
        const symbolsByDate: Record<string, Set<string>> = {};
        const allSymbols = new Set<string>();

        pnlData.forEach((record: any) => {
          if (!valueByDate[record.date]) {
            valueByDate[record.date] = 0;
            symbolsByDate[record.date] = new Set();
          }
          valueByDate[record.date] += record.market_value;
          symbolsByDate[record.date].add(record.symbol);
          allSymbols.add(record.symbol);
        });

        // Keep only dates where at least 80% of symbols have data (filters out partial days)
        const minSymbols = Math.max(1, Math.ceil(allSymbols.size * 0.8));
        const validDates = Object.keys(valueByDate)
          .filter(date => (symbolsByDate[date]?.size || 0) >= minSymbols)
          .sort();

        // Sample weekly for a smoother chart (every 5th trading day)
        const sampledDates = validDates.filter((_, i) => i % 5 === 0 || i === validDates.length - 1);

        const chartData = sampledDates.map(date => ({
          date,
          value: Math.round(valueByDate[date] * 100) / 100,
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

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-5 h-[100px] loading-shimmer" />
          ))}
        </div>
        <div className="glass-card h-[380px] loading-shimmer" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="glass-card p-10 text-center mt-10">
        <p className="text-[var(--negative)] font-mono text-sm">Error loading data. Is the API server running?</p>
        <p className="text-[var(--text-muted)] font-mono text-xs mt-2">Run: ledgerscope serve</p>
      </div>
    );
  }

  return (
    <main>
      <h1 className="section-heading font-sans text-2xl font-semibold text-[var(--text)] mb-8">
        Portfolio Overview
      </h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard 
          label="Total Value" 
          value={`$${summary.total_value.toLocaleString(undefined, {minimumFractionDigits: 2})}`} 
          positive={null} 
        />
        <MetricCard 
          label="Cost Basis" 
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

      {/* Portfolio Value Chart */}
      <div className="glass-card p-6 mb-8">
        <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--text-muted)] mb-5">Portfolio Value Over Time</h2>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={pnl}>
              <defs>
                <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.25} />
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
                formatter={(value: number) => [`$${value.toLocaleString(undefined, {minimumFractionDigits: 2})}`, 'Value']}
              />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="var(--accent)" 
                strokeWidth={2} 
                fill="url(#valueGradient)" 
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Top Holdings Table */}
      <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--text-muted)] mb-4">Top Holdings</h2>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th className="text-left">Symbol</th>
              <th className="text-right">Shares</th>
              <th className="text-right">Avg Cost</th>
              <th className="text-right">Last Trade</th>
            </tr>
          </thead>
          <tbody>
            {holdings.slice(0, 5).map((h) => (
              <tr key={h.symbol}>
                <td className="font-semibold text-[var(--accent)]">{h.symbol}</td>
                <td className="text-right">{h.shares.toFixed(4)}</td>
                <td className="text-right">${h.avg_cost.toFixed(2)}</td>
                <td className="text-right text-[var(--text-dim)]">{h.last_trade_date}</td>
              </tr>
            ))}
            {holdings.length === 0 && (
              <tr>
                <td colSpan={4} className="text-center text-[var(--text-muted)] py-8">No holdings found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

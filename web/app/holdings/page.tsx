"use client";

import { useEffect, useState } from 'react';
import { fetchHoldings, fetchPnL } from '@/lib/api';

export default function HoldingsPage() {
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [holds, pnlHistory] = await Promise.all([
          fetchHoldings(),
          fetchPnL()
        ]);

        // Get latest P&L record for each symbol
        const latestPnl: Record<string, any> = {};
        pnlHistory.forEach((record: any) => {
          if (!latestPnl[record.symbol] || record.date > latestPnl[record.symbol].date) {
            latestPnl[record.symbol] = record;
          }
        });

        const merged = holds.map((h: any) => {
          const p = latestPnl[h.symbol] || {};
          return {
            ...h,
            current_price: p.current_price || h.avg_cost,
            market_value: p.market_value || h.shares * h.avg_cost,
            unrealized_pnl: p.unrealized_pnl || 0
          };
        });

        setHoldings(merged);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="text-text-dim mt-10 text-center animate-pulse">Loading holdings...</div>;

  return (
    <main>
      <h1 className="text-2xl text-accent font-serif italic mb-6">Current Positions</h1>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim">Symbol</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Shares</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Avg Cost</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Current Price</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Market Value</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Unrealized P&L</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => (
              <tr key={h.symbol} className={i % 2 === 0 ? "bg-surface" : "bg-surface2"}>
                <td className="border border-border p-3 font-mono">{h.symbol}</td>
                <td className="border border-border p-3 font-mono text-right">{h.shares.toFixed(4)}</td>
                <td className="border border-border p-3 font-mono text-right">${h.avg_cost.toFixed(2)}</td>
                <td className="border border-border p-3 font-mono text-right">${h.current_price.toFixed(2)}</td>
                <td className="border border-border p-3 font-mono text-right">${h.market_value.toFixed(2)}</td>
                <td className={`border border-border p-3 font-mono text-right ${h.unrealized_pnl >= 0 ? 'text-accent' : 'text-negative'}`}>
                  ${h.unrealized_pnl.toFixed(2)}
                </td>
              </tr>
            ))}
            {holdings.length === 0 && (
              <tr>
                <td colSpan={6} className="border border-border p-3 text-center text-text-dim">No holdings found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

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

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 loading-shimmer rounded-lg" />
        ))}
      </div>
    );
  }

  const totalValue = holdings.reduce((sum, h) => sum + h.market_value, 0);
  const totalPnl = holdings.reduce((sum, h) => sum + h.unrealized_pnl, 0);

  return (
    <main>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="section-heading font-sans text-2xl font-semibold text-[var(--text)]">
          Current Positions
        </h1>
        <div className="text-right">
          <span className="font-mono text-xs text-[var(--text-muted)] uppercase block">Total Value</span>
          <span className="font-mono text-lg text-[var(--text)]">
            ${totalValue.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </span>
          <span className={`font-mono text-xs ml-2 ${totalPnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--negative)]'}`}>
            {totalPnl >= 0 ? '+' : ''}${totalPnl.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </span>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th className="text-left">Symbol</th>
              <th className="text-right">Shares</th>
              <th className="text-right">Avg Cost</th>
              <th className="text-right">Current Price</th>
              <th className="text-right">Market Value</th>
              <th className="text-right">Unrealized P&L</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const pnlPct = h.avg_cost > 0 ? ((h.current_price - h.avg_cost) / h.avg_cost * 100) : 0;
              return (
                <tr key={h.symbol}>
                  <td className="font-semibold text-[var(--accent)]">{h.symbol}</td>
                  <td className="text-right">{h.shares.toFixed(4)}</td>
                  <td className="text-right">${h.avg_cost.toFixed(2)}</td>
                  <td className="text-right">${h.current_price.toFixed(2)}</td>
                  <td className="text-right">${h.market_value.toFixed(2)}</td>
                  <td className={`text-right ${h.unrealized_pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--negative)]'}`}>
                    ${h.unrealized_pnl.toFixed(2)}
                    <span className="text-[var(--text-muted)] text-[11px] ml-1">
                      ({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%)
                    </span>
                  </td>
                </tr>
              );
            })}
            {holdings.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-[var(--text-muted)] py-8">No holdings found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

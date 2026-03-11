"use client";

import { useEffect, useState } from 'react';
import { fetchRisk } from '@/lib/api';

export default function RiskPage() {
  const [risk, setRisk] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchRisk();
        setRisk(data);
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

  return (
    <main>
      <h1 className="section-heading font-sans text-2xl font-semibold text-[var(--text)] mb-8">
        Risk Dashboard
      </h1>
      
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th className="text-left">Symbol</th>
              <th className="text-right">Sharpe</th>
              <th className="text-right">Ann. Volatility</th>
              <th className="text-right">Ann. Return</th>
              <th className="text-right">Worst Day</th>
              <th className="text-right">Trading Days</th>
            </tr>
          </thead>
          <tbody>
            {risk.map((r) => (
              <tr key={r.symbol}>
                <td className="font-semibold text-[var(--accent)]">{r.symbol}</td>
                <td className={`text-right ${r.sharpe !== null && r.sharpe >= 0 ? 'text-[var(--accent)]' : 'text-[var(--negative)]'}`}>
                  {r.sharpe !== null ? r.sharpe.toFixed(4) : "N/A"}
                </td>
                <td className="text-right">
                  {r.annual_vol !== null ? (r.annual_vol * 100).toFixed(2) + "%" : "N/A"}
                </td>
                <td className={`text-right ${r.annual_return !== null && r.annual_return >= 0 ? 'text-[var(--accent)]' : 'text-[var(--negative)]'}`}>
                  {r.annual_return !== null ? (r.annual_return * 100).toFixed(2) + "%" : "N/A"}
                </td>
                <td className="text-right text-[var(--negative)]">
                  {r.worst_day !== null ? (r.worst_day * 100).toFixed(2) + "%" : "N/A"}
                </td>
                <td className="text-right text-[var(--text-dim)]">
                  {r.trading_days ?? "N/A"}
                </td>
              </tr>
            ))}
            {risk.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-[var(--text-muted)] py-8">No risk data available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

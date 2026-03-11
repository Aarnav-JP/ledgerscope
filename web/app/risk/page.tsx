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

  if (loading) return <div className="text-text-dim mt-10 text-center animate-pulse">Loading risk data...</div>;

  return (
    <main>
      <h1 className="text-2xl text-accent font-serif italic mb-6">Risk Dashboard</h1>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim">Symbol</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Sharpe</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Ann. Vol</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Ann. Return</th>
              <th className="border border-border bg-surface2 p-3 font-sans text-xs uppercase text-text-dim text-right">Worst Day</th>
            </tr>
          </thead>
          <tbody>
            {risk.map((r, i) => (
              <tr key={r.symbol} className={i % 2 === 0 ? "bg-surface" : "bg-surface2"}>
                <td className="border border-border p-3 font-mono">{r.symbol}</td>
                <td className={`border border-border p-3 font-mono text-right ${r.sharpe >= 0 ? 'text-accent' : 'text-negative'}`}>
                  {r.sharpe !== null ? r.sharpe.toFixed(4) : "N/A"}
                </td>
                <td className="border border-border p-3 font-mono text-right">
                  {r.annual_vol !== null ? (r.annual_vol * 100).toFixed(2) + "%" : "N/A"}
                </td>
                <td className={`border border-border p-3 font-mono text-right ${r.annual_return >= 0 ? 'text-accent' : 'text-negative'}`}>
                  {r.annual_return !== null ? (r.annual_return * 100).toFixed(2) + "%" : "N/A"}
                </td>
                <td className="border border-border p-3 font-mono text-right text-negative">
                  {r.worst_day !== null ? (r.worst_day * 100).toFixed(2) + "%" : "N/A"}
                </td>
              </tr>
            ))}
            {risk.length === 0 && (
              <tr>
                <td colSpan={5} className="border border-border p-3 text-center text-text-dim">No risk data found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

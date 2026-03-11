export const API_BASE = "http://localhost:8000/api";

export async function fetchHoldings() {
  const res = await fetch(`${API_BASE}/holdings`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch holdings');
  return res.json();
}

export async function fetchRisk() {
  const res = await fetch(`${API_BASE}/risk`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch risk');
  return res.json();
}

export async function fetchPnL(symbol?: string) {
  const url = symbol ? `${API_BASE}/pnl?symbol=${symbol}` : `${API_BASE}/pnl`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch pnl');
  return res.json();
}

export async function fetchSummary() {
  const res = await fetch(`${API_BASE}/summary`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
}

export async function runBacktest(strategy: string, symbol: string, startDate?: string) {
  const res = await fetch(`${API_BASE}/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_sql: strategy, start_date: startDate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to run backtest');
  }
  return res.json();
}

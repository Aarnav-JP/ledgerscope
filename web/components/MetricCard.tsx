import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: string;
  positive?: boolean | null;
}

export default function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  let valueColor = "text-[var(--accent)]";
  if (positive === false) valueColor = "text-[var(--negative)]";
  if (positive === null) valueColor = "text-[var(--text)]";

  return (
    <div className="glass-card p-5 flex flex-col justify-between min-h-[100px] group">
      <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-3 block">
        {label}
      </span>
      <div>
        <span className={`font-mono text-2xl tracking-tight ${valueColor} transition-colors`}>
          {value}
        </span>
        {delta && (
          <span className={`block font-sans text-xs mt-2 ${positive === false ? 'text-[var(--negative)]' : 'text-[var(--text-dim)]'}`}>
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}

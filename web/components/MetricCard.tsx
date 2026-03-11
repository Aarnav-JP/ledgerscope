import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: string;
  positive?: boolean | null;
}

export default function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  let valueColor = "text-accent";
  if (positive === false) valueColor = "text-negative";
  if (positive === null) valueColor = "text-text";

  return (
    <div className="bg-surface border border-border p-4 sm:p-5 rounded-none flex flex-col justify-center">
      <span className="font-mono text-[10px] uppercase text-text-muted mb-2 block truncate">{label}</span>
      <span className={`font-mono text-xl sm:text-2xl tracking-tighter break-words ${valueColor}`}>{value}</span>
      {delta && <span className="font-sans text-xs text-text-dim mt-2 truncate">{delta}</span>}
    </div>
  );
}

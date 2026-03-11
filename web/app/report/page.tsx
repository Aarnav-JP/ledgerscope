"use client";

import { API_BASE } from '@/lib/api';
import { useState } from 'react';

export default function ReportPage() {
  const [generating, setGenerating] = useState(false);

  const handleDownload = () => {
    setGenerating(true);
    window.open(`${API_BASE}/report/pdf`, "_blank");
    setTimeout(() => setGenerating(false), 3000);
  };

  return (
    <main className="flex flex-col items-center justify-center mt-16">
      <h1 className="section-heading font-sans text-2xl font-semibold text-[var(--text)] mb-4 text-center">
        Generate Report
      </h1>
      <p className="text-[var(--text-dim)] font-sans text-sm max-w-md text-center mb-10 leading-relaxed">
        Generate a comprehensive PDF report of your portfolio including summary, risk metrics, holdings, benchmarks, and a portfolio value chart.
      </p>
      
      <div className="glass-card p-8 max-w-md w-full">
        <div className="space-y-4 mb-8">
          {[
            { label: "Data Source", value: "DuckDB (Local)" },
            { label: "Format", value: "A4 PDF" },
            { label: "Engine", value: "WeasyPrint + Jinja2" },
            { label: "Charts", value: "Matplotlib" },
          ].map(item => (
            <div key={item.label} className="flex justify-between items-center border-b border-[var(--border)] pb-3">
              <span className="font-mono text-xs text-[var(--text-muted)] uppercase">{item.label}</span>
              <span className="font-mono text-sm text-[var(--text)]">{item.value}</span>
            </div>
          ))}
        </div>

        <button 
          onClick={handleDownload}
          disabled={generating}
          className="btn-accent w-full"
        >
          {generating ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-[var(--bg)] border-t-transparent rounded-full animate-spin" />
              Generating...
            </span>
          ) : "Generate & Download PDF"}
        </button>
      </div>
    </main>
  );
}

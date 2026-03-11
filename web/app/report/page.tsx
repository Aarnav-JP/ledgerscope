"use client";

import { API_BASE } from '@/lib/api';

export default function ReportPage() {
  const handleDownload = () => {
    window.open(`${API_BASE}/report/pdf`, "_blank");
  };

  return (
    <main className="flex flex-col items-center justify-center text-center mt-20">
      <h1 className="text-3xl text-accent font-serif italic mb-6">Generate PDF Report</h1>
      <p className="text-text-dim max-w-lg mb-8">
        Generate a comprehensive printable PDF report of your entire portfolio, 
        including account summary, value over time, risk metrics, individual holdings, 
        and benchmark comparisons.
      </p>
      
      <div className="bg-surface border border-border p-10 max-w-lg w-full">
        <div className="text-left mb-8 flex flex-col gap-3 font-mono text-sm text-text-muted">
          <div className="flex justify-between border-b border-border pb-2">
            <span>Data</span>
            <span className="text-text">Live (DuckDB)</span>
          </div>
          <div className="flex justify-between border-b border-border pb-2">
            <span>Format</span>
            <span className="text-text">A4 PDF</span>
          </div>
          <div className="flex justify-between border-b border-border pb-2">
            <span>Engine</span>
            <span className="text-text">WeasyPrint</span>
          </div>
        </div>

        <button 
          onClick={handleDownload}
          className="w-full bg-accent text-bg font-sans font-semibold py-3 px-6 hover:bg-opacity-80 transition-opacity"
        >
          Generate & Download PDF
        </button>
      </div>
    </main>
  );
}

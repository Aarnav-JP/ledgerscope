import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const ibmSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-ibm-sans"
});

const ibmMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-mono"
});

export const metadata: Metadata = {
  title: "LedgerScope — Portfolio Analytics",
  description: "SQL-Native Portfolio Risk Analytics Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${ibmSans.variable} ${ibmMono.variable} font-sans antialiased`}>
        <div className="max-w-[1100px] mx-auto min-h-screen px-6 py-8">
          {/* Header / Brand */}
          <header className="mb-10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center text-[var(--bg)] font-bold text-sm">
                  LS
                </div>
                <span className="font-sans font-semibold text-lg tracking-tight text-[var(--text)]">
                  Ledger<span className="text-[var(--accent)]">Scope</span>
                </span>
              </div>
              <span className="font-mono text-xs text-[var(--text-muted)] hidden sm:block">
                SQL-Native Analytics
              </span>
            </div>

            {/* Navigation */}
            <nav className="glass-surface px-2 py-1 flex gap-1 overflow-x-auto">
              {[
                { href: "/", label: "Overview" },
                { href: "/holdings", label: "Holdings" },
                { href: "/risk", label: "Risk" },
                { href: "/backtest", label: "Backtest" },
                { href: "/report", label: "Report" },
                { href: "/settings", label: "⚙️ Settings" },
              ].map(link => (
                <a
                  key={link.href}
                  href={link.href}
                  className="px-4 py-2.5 rounded-lg font-sans text-sm font-medium text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--accent-dim)] transition-all duration-200 whitespace-nowrap"
                >
                  {link.label}
                </a>
              ))}
            </nav>
          </header>

          {/* Page Content */}
          <div className="page-enter">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}

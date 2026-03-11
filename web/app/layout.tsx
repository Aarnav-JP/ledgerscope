import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const ibmSans = IBM_Plex_Sans({ 
  subsets: ["latin"], 
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-sans"
});

const ibmMono = IBM_Plex_Mono({ 
  subsets: ["latin"], 
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-mono"
});

export const metadata: Metadata = {
  title: "LedgerScope",
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
        <div className="max-w-[900px] mx-auto min-h-screen px-4 py-8">
          <nav className="mb-8 flex space-x-6 border-b border-border pb-4">
            <a href="/" className="text-text hover:text-accent font-semibold transition-colors">Overview</a>
            <a href="/holdings" className="text-text hover:text-accent transition-colors">Holdings</a>
            <a href="/risk" className="text-text hover:text-accent transition-colors">Risk Dashboard</a>
            <a href="/backtest" className="text-text hover:text-accent transition-colors">Backtest</a>
            <a href="/report" className="text-text hover:text-accent transition-colors">Report</a>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}

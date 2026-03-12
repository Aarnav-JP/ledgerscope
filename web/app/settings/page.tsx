"use client";

import { useEffect, useState } from 'react';

interface Config {
    general: {
        base_currency: string;
        risk_free_rate: number;
        log_level: string;
    };
    data: {
        cache_expiry_days: number;
        retry_attempts: number;
    };
    currency: {
        auto_convert: boolean;
    };
    display: {
        date_format: string;
        decimal_places: number;
        large_number_format: string;
    };
}

interface CurrencyInfo {
    base_currency: string;
    currencies: string[];
    exchange_rates: Record<string, number | null>;
}

export default function SettingsPage() {
    const [config, setConfig] = useState<Config | null>(null);
    const [currencies, setCurrencies] = useState<CurrencyInfo | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'config' | 'currencies' | 'logs'>('config');

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [configRes, currencyRes, logsRes] = await Promise.all([
                fetch('http://localhost:8000/api/config'),
                fetch('http://localhost:8000/api/currencies'),
                fetch('http://localhost:8000/api/logs?lines=50')
            ]);

            const configData = await configRes.json();
            const logsData = await logsRes.json();

            setConfig(configData);
            setLogs(logsData.logs || []);

            // Handle currency data separately (may fail if DB is not initialized)
            if (currencyRes.ok) {
                const currencyData = await currencyRes.json();
                setCurrencies(currencyData);
            } else {
                console.error('Failed to load currencies:', await currencyRes.text());
                setCurrencies({ base_currency: 'USD', currencies: [], exchange_rates: {} });
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="space-y-6">
                <h1 className="text-3xl font-bold text-white mb-6">Settings</h1>
                <div className="glass-card p-8 loading-shimmer h-[400px]" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-white mb-6">Settings</h1>

            {/* Tab Navigation */}
            <div className="flex space-x-2 border-b border-gray-700">
                <button
                    onClick={() => setActiveTab('config')}
                    className={`px-6 py-3 font-mono text-sm transition-colors ${activeTab === 'config'
                            ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                >
                    Configuration
                </button>
                <button
                    onClick={() => setActiveTab('currencies')}
                    className={`px-6 py-3 font-mono text-sm transition-colors ${activeTab === 'currencies'
                            ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                >
                    Currencies
                </button>
                <button
                    onClick={() => setActiveTab('logs')}
                    className={`px-6 py-3 font-mono text-sm transition-colors ${activeTab === 'logs'
                            ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                >
                    Logs
                </button>
            </div>

            {/* Configuration Tab */}
            {activeTab === 'config' && config && (
                <div className="space-y-6">
                    {/* General Settings */}
                    <div className="glass-card p-6">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center">
                            <span className="mr-2">⚙️</span>
                            General Settings
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Base Currency
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono font-bold">
                                        {config.general.base_currency}
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Risk-Free Rate
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {(config.general.risk_free_rate * 100).toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Log Level
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {config.general.log_level}
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Cache Expiry
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {config.data.cache_expiry_days} day(s)
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Display Settings */}
                    <div className="glass-card p-6">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center">
                            <span className="mr-2">🎨</span>
                            Display Settings
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Date Format
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {config.display.date_format}
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Decimal Places
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {config.display.decimal_places}
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-mono text-gray-400 mb-2">
                                    Large Number Format
                                </label>
                                <div className="bg-[var(--bg-secondary)] p-3 rounded border border-gray-700">
                                    <span className="text-white font-mono">
                                        {config.display.large_number_format}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-4 bg-blue-900/20 border-blue-500/30">
                        <p className="text-sm text-gray-300 font-mono">
                            💡 <strong>Tip:</strong> To change settings, use the CLI:{' '}
                            <code className="bg-gray-800 px-2 py-1 rounded">
                                ledgerscope config-set general.base_currency EUR
                            </code>
                        </p>
                    </div>
                </div>
            )}

            {/* Currencies Tab */}
            {activeTab === 'currencies' && currencies && (
                <div className="space-y-6">
                    <div className="glass-card p-6">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center">
                            <span className="mr-2">💱</span>
                            Multi-Currency Support
                        </h2>

                        <div className="mb-6">
                            <label className="block text-sm font-mono text-gray-400 mb-2">
                                Base Currency
                            </label>
                            <div className="bg-[var(--bg-secondary)] p-4 rounded border border-gray-700 inline-block">
                                <span className="text-2xl font-mono font-bold text-[var(--accent)]">
                                    {currencies.base_currency}
                                </span>
                            </div>
                        </div>

                        <h3 className="text-lg font-bold text-white mb-3">
                            Portfolio Currencies & Exchange Rates
                        </h3>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-gray-700">
                                        <th className="text-left py-3 px-4 font-mono text-sm text-gray-400">
                                            Currency
                                        </th>
                                        <th className="text-left py-3 px-4 font-mono text-sm text-gray-400">
                                            Pair
                                        </th>
                                        <th className="text-right py-3 px-4 font-mono text-sm text-gray-400">
                                            Exchange Rate
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {currencies.currencies?.map((currency) => {
                                        const rate = currencies.exchange_rates?.[currency];
                                        return (
                                            <tr
                                                key={currency}
                                                className="border-b border-gray-800 hover:bg-gray-800/30"
                                            >
                                                <td className="py-3 px-4">
                                                    <span className="font-mono font-bold text-white">
                                                        {currency}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className="font-mono text-gray-400">
                                                        {currency}/{currencies.base_currency}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-right">
                                                    {currency === currencies.base_currency ? (
                                                        <span className="font-mono text-gray-500">
                                                            1.0000 (base)
                                                        </span>
                                                    ) : rate !== null ? (
                                                        <span className="font-mono text-white">
                                                            {rate.toFixed(4)}
                                                        </span>
                                                    ) : (
                                                        <span className="font-mono text-[var(--negative)]">
                                                            Not available
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="glass-card p-4 bg-green-900/20 border-green-500/30">
                        <p className="text-sm text-gray-300 font-mono">
                            ✅ <strong>Status:</strong> Exchange rates are automatically fetched and cached.
                            To refresh, use:{' '}
                            <code className="bg-gray-800 px-2 py-1 rounded">
                                ledgerscope ingest &lt;broker&gt; &lt;file&gt; --refresh
                            </code>
                        </p>
                    </div>
                </div>
            )}

            {/* Logs Tab */}
            {activeTab === 'logs' && (
                <div className="space-y-6">
                    <div className="glass-card p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold text-white flex items-center">
                                <span className="mr-2">📝</span>
                                Recent Logs
                            </h2>
                            <button
                                onClick={loadData}
                                className="px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded font-mono text-sm transition-colors"
                            >
                                Refresh
                            </button>
                        </div>

                        <div className="bg-gray-900 p-4 rounded border border-gray-700 font-mono text-xs overflow-x-auto max-h-[500px] overflow-y-auto">
                            {logs.length > 0 ? (
                                logs.map((log, idx) => (
                                    <div
                                        key={idx}
                                        className={`py-1 ${log.includes('ERROR')
                                                ? 'text-red-400'
                                                : log.includes('WARNING')
                                                    ? 'text-yellow-400'
                                                    : log.includes('INFO')
                                                        ? 'text-blue-400'
                                                        : 'text-gray-400'
                                            }`}
                                    >
                                        {log}
                                    </div>
                                ))
                            ) : (
                                <div className="text-gray-500 text-center py-4">
                                    No logs available
                                </div>
                            )}
                        </div>

                        <div className="mt-4 text-xs text-gray-400 font-mono">
                            Showing last {logs.length} lines. Full logs at:{' '}
                            <code className="text-[var(--accent)]">~/.ledgerscope/ledgerscope.log</code>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

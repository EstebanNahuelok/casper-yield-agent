import { useMemo, useState } from "react";

import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import {
    Wallet,
    TrendingUp,
    PieChart,
    Activity,
    ArrowUpRight,
    Coins,
    DollarSign,
    BarChart3,
} from "lucide-react";

import { useAgentStatus } from "#hooks/useAgentStatus";
import { useAgentConfig } from "#hooks/useAgentConfig";

const RANGES = ["1D", "7D", "1M", "3M", "1Y", "ALL"] as const;
type Range = (typeof RANGES)[number];

function timeAgo(iso: string): string {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "—";
    const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (s >= 3600) return `${Math.floor(s / 3600)}h ago`;
    if (s >= 60) return `${Math.floor(s / 60)}m ago`;
    return `${s}s ago`;
}

export const PortfolioPage = () => {
    const [range, setRange] = useState<Range>("7D");
    const { status } = useAgentStatus();
    const config = useAgentConfig();

    const balanceCspr = status?.balance_cspr ?? 0;
    const csprPriceUsd = status?.last_market_data?.cspr_price_usd ?? 0;
    const poolApy = status?.last_market_data?.pool_apy ?? null;
    const portfolioUsd = balanceCspr * csprPriceUsd;

    // Build activity chart from real decision_history
    const activityData = useMemo(() => {
        const history = [...(status?.decision_history ?? [])].reverse();
        return history.map((d) => ({
            label: d.timestamp
                ? new Date(d.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "—",
            value: d.action === "SWAP" ? 1 : 0.45,
            action: d.action,
        }));
    }, [status?.decision_history]);

    // Allocation: if last decision was SWAP we have some sCSPR, otherwise 100% CSPR
    const hadSwap = status?.last_decision?.action === "SWAP";
    const csprPct = hadSwap ? 79 : 100;
    const scsprPct = hadSwap ? 21 : 0;

    // Vault address truncated
    const vaultKey = config.vault_public_key;
    const vaultDisplay = vaultKey
        ? `${vaultKey.slice(0, 20)}...`
        : "—";

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-300">
            <main className="mx-auto max-w-7xl px-6 py-10">
                {/* Header */}
                <div className="mb-10">
                    <div className="text-[10px] uppercase tracking-widest text-brand font-mono mb-2">
                        Portfolio
                    </div>
                    <h1 className="text-4xl font-semibold tracking-tight text-zinc-100">
                        Agent Portfolio
                    </h1>
                    <p className="mt-3 text-zinc-500 max-w-2xl">
                        Real-time overview of vault assets, active positions and autonomous
                        trading activity.
                    </p>
                </div>

                {/* Total Value */}
                <section className="mb-10">
                    <div className="text-center">
                        <div className="text-sm uppercase tracking-widest text-zinc-500">
                            Portfolio Value
                        </div>
                        <div className="mt-3 text-6xl font-semibold text-zinc-100">
                            {csprPriceUsd > 0
                                ? `$${portfolioUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                : `${balanceCspr.toLocaleString()} CSPR`}
                        </div>
                        {csprPriceUsd > 0 && (
                            <div className="mt-2 text-zinc-500 font-mono text-sm">
                                {balanceCspr.toLocaleString()} CSPR · ${csprPriceUsd.toFixed(5)}/CSPR
                            </div>
                        )}
                    </div>

                    <div className="mt-8 flex justify-center">
                        <div className="inline-flex rounded-xl border border-zinc-800 bg-zinc-900/40 p-1">
                            {RANGES.map((r) => (
                                <button
                                    key={r}
                                    onClick={() => setRange(r)}
                                    className={`
                                        px-4 py-2 rounded-lg text-xs font-mono transition
                                        ${range === r
                                            ? "bg-red-500 text-zinc-950"
                                            : "text-zinc-500 hover:text-zinc-200"
                                        }
                                    `}
                                >
                                    {r}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4">
                            Agent Activity · Last decisions
                        </div>
                        <div className="h-[280px]">
                            {activityData.length === 0 ? (
                                <div className="h-full flex items-center justify-center rounded-lg border border-dashed border-zinc-800 text-xs font-mono text-zinc-600">
                                    No decisions recorded yet
                                </div>
                            ) : (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={activityData} margin={{ top: 10, right: 4, left: -28, bottom: 0 }}>
                                        <CartesianGrid stroke="#18181b" vertical={false} />
                                        <XAxis
                                            dataKey="label"
                                            stroke="#52525b"
                                            tick={{ fontSize: 10 }}
                                            tickLine={false}
                                            axisLine={false}
                                        />
                                        <YAxis hide domain={[0, 1]} />
                                        <Tooltip
                                            content={({ active, payload }) => {
                                                if (!active || !payload?.length) return null;
                                                const d = payload[0].payload;
                                                return (
                                                    <div className="rounded-md border border-zinc-800 bg-zinc-950/95 px-3 py-2 text-[11px] font-mono shadow-xl">
                                                        <span className={d.action === "SWAP" ? "text-emerald-400" : "text-zinc-400"}>
                                                            {d.action}
                                                        </span>
                                                        <span className="text-zinc-600 ml-2">{d.label}</span>
                                                    </div>
                                                );
                                            }}
                                            cursor={{ fill: "#ffffff08" }}
                                        />
                                        <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={28}>
                                            {activityData.map((d, i) => (
                                                <Cell key={i} fill={d.action === "SWAP" ? "#10b981" : "#3f3f46"} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            )}
                        </div>
                    </div>
                </section>

                {/* Assets */}
                <section className="grid gap-4 md:grid-cols-4 mb-8">
                    {[
                        {
                            title: "Total Assets",
                            value: balanceCspr > 0 ? `${balanceCspr.toLocaleString()} CSPR` : "—",
                            icon: Coins,
                        },
                        {
                            title: "Today's PnL",
                            value: status?.last_decision?.action === "SWAP" && status.last_decision.amount_out != null
                                ? `+${status.last_decision.amount_out.toFixed(4)} sCSPR`
                                : "—",
                            icon: DollarSign,
                        },
                        {
                            title: "Pool APY",
                            value: poolApy != null ? `${poolApy.toFixed(2)}%` : "—",
                            icon: TrendingUp,
                        },
                        {
                            title: "Executed Swaps",
                            value: status?.actions_taken != null ? String(status.actions_taken) : "—",
                            icon: BarChart3,
                        },
                    ].map((item) => {
                        const Icon = item.icon;
                        return (
                            <div
                                key={item.title}
                                className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5"
                            >
                                <div className="flex items-center justify-between">
                                    <span className="text-xs uppercase tracking-widest text-zinc-500">
                                        {item.title}
                                    </span>
                                    <Icon size={16} className="text-brand" />
                                </div>
                                <div className="mt-4 text-2xl font-semibold text-zinc-100">
                                    {item.value}
                                </div>
                            </div>
                        );
                    })}
                </section>

                <section className="grid gap-6 lg:grid-cols-2 mb-8">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex items-center gap-2 mb-5">
                            <PieChart size={18} className="text-brand" />
                            <h2 className="text-zinc-100 font-medium">Asset Allocation</h2>
                        </div>
                        <div className="space-y-6">
                            <div>
                                <div className="flex justify-between mb-2">
                                    <span>CSPR</span>
                                    <span>{csprPct}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-zinc-800">
                                    <div
                                        className="h-full rounded-full bg-brand transition-all duration-500"
                                        style={{ width: `${csprPct}%` }}
                                    />
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between mb-2">
                                    <span>sCSPR</span>
                                    <span>{scsprPct}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-zinc-800">
                                    <div
                                        className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                                        style={{ width: `${scsprPct}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex items-center gap-2 mb-5">
                            <Wallet size={18} className="text-brand" />
                            <h2 className="text-zinc-100 font-medium">Wallet Information</h2>
                        </div>
                        <div className="space-y-4 text-sm">
                            <div>
                                <div className="text-zinc-500 mb-1">Network</div>
                                <div className="font-mono capitalize">Casper {config.casper_network}</div>
                            </div>
                            <div>
                                <div className="text-zinc-500 mb-1">Vault Address</div>
                                <div className="font-mono break-all">{vaultDisplay}</div>
                            </div>
                            <div>
                                <div className="text-zinc-500 mb-1">Strategy</div>
                                <div className="font-mono">
                                    APY Threshold +{config.min_apy_delta}% · Slip ≤ {config.max_slippage_pct}%
                                </div>
                            </div>
                            <div>
                                <div className="text-zinc-500 mb-1">Cycle</div>
                                <div className="font-mono">{config.check_interval_seconds}s</div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Active Positions */}
                <section className="mb-8">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <h2 className="text-zinc-100 font-medium mb-6">Active Positions</h2>
                        <div className="space-y-4">
                            {status?.last_decision ? (
                                <div className="flex items-center justify-between rounded-lg border border-zinc-800 p-4">
                                    <div>
                                        <div className="text-zinc-100">CSPR / sCSPR</div>
                                        <div className="text-zinc-500 text-sm">
                                            APY {poolApy != null ? `${poolApy.toFixed(2)}%` : "—"}
                                        </div>
                                    </div>
                                    <span className={`rounded-full border px-3 py-1 text-xs ${
                                        status.last_decision.action === "SWAP"
                                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                                            : "border-zinc-700 bg-zinc-800 text-zinc-400"
                                    }`}>
                                        {status.last_decision.action === "SWAP" ? "Staked" : "Monitoring"}
                                    </span>
                                </div>
                            ) : (
                                <div className="py-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg">
                                    No positions yet — agent monitoring
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* Recent Activity */}
                <section>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex items-center gap-2 mb-6">
                            <Activity size={18} className="text-brand" />
                            <h2 className="text-zinc-100 font-medium">Recent Agent Activity</h2>
                        </div>
                        <div className="space-y-4">
                            {(status?.decision_history ?? []).length === 0 ? (
                                <div className="py-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg">
                                    No decisions recorded yet
                                </div>
                            ) : (
                                status.decision_history.slice(0, 5).map((d: any, i: number) => (
                                    <div
                                        key={i}
                                        className="flex items-center justify-between rounded-lg border border-zinc-800 p-4"
                                    >
                                        <div>
                                            <div className={`font-medium ${d.action === "SWAP" ? "text-emerald-400" : "text-zinc-100"}`}>
                                                {d.action}
                                            </div>
                                            <div className="text-sm text-zinc-500 text-pretty max-w-sm">
                                                {d.reasoning || "—"}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 text-zinc-500 text-sm shrink-0">
                                            {d.timestamp ? timeAgo(d.timestamp) : "—"}
                                            <ArrowUpRight size={14} />
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
};

import { useMemo, useState } from "react";

import {
    Area,
    AreaChart,
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
    Shield,
    Coins,
    DollarSign,
    BarChart3,
} from "lucide-react";
const RANGES = ["1D", "7D", "1M", "3M", "1Y", "ALL"] as const;

type Range = (typeof RANGES)[number];
export const PortfolioPage = () => {
    const [range, setRange] = useState<Range>("7D");
    const chartData = useMemo(
        () => [
            { day: "1", value: 36500 },
            { day: "2", value: 37200 },
            { day: "3", value: 36800 },
            { day: "4", value: 38100 },
            { day: "5", value: 39700 },
            { day: "6", value: 40800 },
            { day: "7", value: 42176 },
        ],
        []
    );
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
                            $42,176.38
                        </div>

                        <div className="mt-3 flex items-center justify-center gap-2 text-emerald-400">
                            <TrendingUp size={18} />
                            <span className="font-mono">
                                +4.21% Today
                            </span>
                        </div>
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
                                            ? "bg-brand text-zinc-950"
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
                        <div className="h-[350px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={chartData}>
                                    <defs>
                                        <linearGradient
                                            id="portfolioGradient"
                                            x1="0"
                                            y1="0"
                                            x2="0"
                                            y2="1"
                                        >
                                            <stop
                                                offset="0%"
                                                stopColor="#ff2d2d"
                                                stopOpacity={0.4}
                                            />
                                            <stop
                                                offset="100%"
                                                stopColor="#ff2d2d"
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                    </defs>

                                    <XAxis
                                        dataKey="day"
                                        stroke="#52525b"
                                    />

                                    <YAxis stroke="#52525b" />

                                    <Tooltip />

                                    <Area
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#ff2d2d"
                                        strokeWidth={2}
                                        fill="url(#portfolioGradient)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </section>

                {/* Assets */}
                <section className="grid gap-4 md:grid-cols-4 mb-8">
                    {[
                        {
                            title: "Total Assets",
                            value: "1,240,482",
                            icon: Coins,
                        },
                        {
                            title: "Today's PnL",
                            value: "+$1,842",
                            icon: DollarSign,
                        },
                        {
                            title: "Average APY",
                            value: "18.4%",
                            icon: TrendingUp,
                        },
                        {
                            title: "Active Pools",
                            value: "6",
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
                            <h2 className="text-zinc-100 font-medium">
                                Asset Allocation
                            </h2>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <div className="flex justify-between mb-2">
                                    <span>CSPR</span>
                                    <span>79%</span>
                                </div>

                                <div className="h-2 rounded-full bg-zinc-800">
                                    <div
                                        className="h-full rounded-full bg-brand"
                                        style={{ width: "79%" }}
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between mb-2">
                                    <span>sCSPR</span>
                                    <span>21%</span>
                                </div>

                                <div className="h-2 rounded-full bg-zinc-800">
                                    <div
                                        className="h-full rounded-full bg-emerald-500"
                                        style={{ width: "21%" }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex items-center gap-2 mb-5">
                            <Wallet size={18} className="text-brand" />
                            <h2 className="text-zinc-100 font-medium">
                                Wallet Information
                            </h2>
                        </div>

                        <div className="space-y-4 text-sm">
                            <div>
                                <div className="text-zinc-500 mb-1">
                                    Network
                                </div>

                                <div className="font-mono">
                                    Casper Testnet
                                </div>
                            </div>

                            <div>
                                <div className="text-zinc-500 mb-1">
                                    Vault Address
                                </div>

                                <div className="font-mono break-all">
                                    0202ca422d30d0335415bd64fe98e5508...
                                </div>
                            </div>

                            <div>
                                <div className="text-zinc-500 mb-1">
                                    Strategy
                                </div>

                                <div className="font-mono">
                                    APY Threshold +2%
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Active Positions */}

                <section className="mb-8">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <h2 className="text-zinc-100 font-medium mb-6">
                            Active Positions
                        </h2>

                        <div className="space-y-4">
                            {[
                                {
                                    pair: "CSPR / USDT",
                                    apy: "18.4%",
                                    status: "Staked",
                                },
                                {
                                    pair: "CSPR / USDC",
                                    apy: "16.8%",
                                    status: "Entry Queued",
                                },
                            ].map((pool) => (
                                <div
                                    key={pool.pair}
                                    className="flex items-center justify-between rounded-lg border border-zinc-800 p-4"
                                >
                                    <div>
                                        <div className="text-zinc-100">
                                            {pool.pair}
                                        </div>

                                        <div className="text-zinc-500 text-sm">
                                            APY {pool.apy}
                                        </div>
                                    </div>

                                    <span className="rounded-full border border-brand/20 bg-brand/10 px-3 py-1 text-xs text-brand">
                                        {pool.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Recent Activity */}

                <section>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex items-center gap-2 mb-6">
                            <Activity size={18} className="text-brand" />

                            <h2 className="text-zinc-100 font-medium">
                                Recent Agent Activity
                            </h2>
                        </div>

                        <div className="space-y-4">
                            {[
                                {
                                    type: "SWAP",
                                    text: "420 CSPR → sCSPR",
                                    time: "2 min ago",
                                },
                                {
                                    type: "HOLD",
                                    text: "APY threshold not reached",
                                    time: "7 min ago",
                                },
                                {
                                    type: "SWAP",
                                    text: "200 CSPR → sCSPR",
                                    time: "12 min ago",
                                },
                            ].map((item, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between rounded-lg border border-zinc-800 p-4"
                                >
                                    <div>
                                        <div className="text-zinc-100">
                                            {item.type}
                                        </div>

                                        <div className="text-sm text-zinc-500">
                                            {item.text}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 text-zinc-500 text-sm">
                                        {item.time}
                                        <ArrowUpRight size={14} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
};
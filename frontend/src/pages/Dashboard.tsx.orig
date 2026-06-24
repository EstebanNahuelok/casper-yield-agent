import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,

} from "recharts";
import {
    Bot, ChevronDown, ChevronRight, ExternalLink, Info, Wallet, X, Vault,
    ArrowRightLeft, ChevronLeft,
    Send, Zap,
} from "lucide-react";
import { useCasperTransaction } from "#hooks/useCasperTransaction";
const EXPLORER = "https://testnet.cspr.live/deploy/";

// ---------- i18n ----------

type Lang = "en" | "es";

const dict = {
    en: {
        agentActive: "Agent Active",
        nextCycle: "Next cycle",
        testnetNode: "Testnet Node",
        connectWallet: "Connect wallet",
        totalVaultBalance: "{t.totalVaultBalance}",
        rangeChange: "Change",
        activePositions: "Active Positions",
        totalDeploys: "Total Deploys",
        agentStrategy: "Agent Strategy",
        apyThreshold: "APY Threshold",
        strategyDesc:
            "Dynamic liquidity provisioning with auto-compounding on Casper testnet pools. Sensitivity adjusted for low-volatility events.",
        updateStrategy: "Update Strategy",
        onchainTelemetry: "On-chain Telemetry",
        telemetrySub: "Gas price & node latency",
        window: "window",
        gasPrice: "Gas price",
        nodeLatency: "Node latency",
        opportunityScanner: "Opportunity Scanner",
        clickPool: "Click a pool to inspect",
        poolName: "Pool Name",
        status: "Status",
        scannerHint:
            "The agent has identified a yield imbalance in the CSPR/USDC pool. Deployment scheduled for next epoch transition (approx. 42 minutes).",
        reasoningFeed: "Autonomous Reasoning Feed",
        expandDrill: "Expand for drill-down",
        viewAudit: "View Audit Logs",
        connected: "CONNECTED",
        poolDetail: "Pool detail",
        position: "Position",
        rewards24h: "Rewards 24h",
        apyLast24h: "APY · last 24h",
        agentReasoning: "Agent reasoning",
        riskProfile: "Risk profile",
        impermanentLoss: "Impermanent loss",
        scRisk: "Smart-contract risk",
        audited: "Audited",
        oracleSource: "Oracle source",
        forceEntry: "Force entry",
        blacklist: "Blacklist",
        inputs: "Inputs",
        reasoningTrace: "Reasoning trace",
        viewExplorer: "View on explorer",
    },
    es: {
        agentActive: "Agente activo",
        nextCycle: "Próximo ciclo",
        testnetNode: "Nodo testnet",
        connectWallet: "Conectar wallet",
        totalVaultBalance: "Balance total del vault",
        rangeChange: "Variación",
        activePositions: "Posiciones activas",
        totalDeploys: "Despliegues totales",
        agentStrategy: "Estrategia del agente",
        apyThreshold: "Umbral de APY",
        strategyDesc:
            "Provisión dinámica de liquidez con auto-compounding en pools de Casper testnet. Sensibilidad ajustada para eventos de baja volatilidad.",
        updateStrategy: "Actualizar estrategia",
        onchainTelemetry: "Telemetría on-chain",
        telemetrySub: "Precio de gas y latencia del nodo",
        window: "ventana",
        gasPrice: "Precio de gas",
        nodeLatency: "Latencia del nodo",
        opportunityScanner: "Escáner de oportunidades",
        clickPool: "Hacé clic en un pool para inspeccionar",
        poolName: "Pool",
        status: "Estado",
        scannerHint:
            "El agente detectó un desequilibrio de rendimiento en el pool CSPR/USDC. Despliegue programado para la próxima transición de epoch (aprox. 42 minutos).",
        reasoningFeed: "Feed de razonamiento autónomo",
        expandDrill: "Expandir para ver detalle",
        viewAudit: "Ver logs de auditoría",
        connected: "CONECTADO",
        poolDetail: "Detalle del pool",
        position: "Posición",
        rewards24h: "Rewards 24h",
        apyLast24h: "APY · últimas 24h",
        agentReasoning: "Razonamiento del agente",
        riskProfile: "Perfil de riesgo",
        impermanentLoss: "Impermanent loss",
        scRisk: "Riesgo de smart-contract",
        audited: "Auditado",
        oracleSource: "Fuente de oráculo",
        forceEntry: "Forzar entrada",
        blacklist: "Lista negra",
        inputs: "Entradas",
        reasoningTrace: "Traza de razonamiento",
        viewExplorer: "Ver en el explorer",
    },
} as const;

type Dict = { [K in keyof typeof dict.en]: string };
const LangContext = createContext<{ lang: Lang; t: Dict }>({ lang: "en", t: dict.en });
const useT = () => useContext(LangContext).t;
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "#components/ui/sheet";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "#components/ui/collapsible";
import { WalletConnect } from "#components/WalletConnect";
import { ProfileMenu } from "#components/ProfileOptions";
import { Link } from "react-router-dom";
import { useAgentStatus } from "#hooks/useAgentStatus";
import { useAgentWallet } from "../context/AgentWalletContext";



// ---------- data ----------

type Pool = {
    pair: string;
    apy: string;
    apyNum: number;
    tvl: string;
    status: string;
    tone: "emerald" | "zinc" | "brand";
    muted?: boolean;
    protocol: string;
    fee: string;
    position: string;
    rewards24h: string;
    impermanentLoss: string;
    reasoning: string;
};

const pools: Pool[] = [
    {
        pair: "CSPR / sCSPR",
        apy: "18.70%",
        apyNum: 18.70,
        tvl: "1.85M CSPR",
        status: "Staked",
        tone: "emerald",
        protocol: "Casper Yield Vault",
        fee: "0.15%",
        position: "842,500 CSPR",
        rewards24h: "+128.45 CSPR",
        impermanentLoss: "0.00%",
        reasoning: "Pool nativo con el mejor rendimiento actual.",
    },
];
type Decision = {
    id: string;
    when: string;
    tx: string;
    deployHash: string;
    title: string;
    text: string;
    tone: "brand" | "emerald" | "zinc";
    status: "Success" | "Pending" | "Observation";
    inputs: { label: string; value: string }[];
    reasoning: string[];
};



// Trend data generators
const RANGES = ["1H", "24H", "7D", "30D"] as const;
type Range = (typeof RANGES)[number];

function buildSeries(range: Range) {
    const points = range === "1H" ? 12 : range === "24H" ? 24 : range === "7D" ? 28 : 30;
    const base = 1_180_000;
    const data = [];
    for (let i = 0; i < points; i++) {
        const drift = Math.sin(i / 2.4) * 18000 + Math.cos(i / 1.7) * 9000;
        const growth = (i / points) * 60000;
        const noise = (Math.sin(i * 7.13) + Math.cos(i * 3.11)) * 4000;
        data.push({
            idx: i,
            label:
                range === "1H"
                    ? `${(i * 5).toString().padStart(2, "0")}m`
                    : range === "24H"
                        ? `${i.toString().padStart(2, "0")}h`
                        : range === "7D"
                            ? `D${Math.floor(i / 4) + 1}`
                            : `D${i + 1}`,
            balance: Math.round(base + drift + growth + noise),
            gas: Math.max(0.6, 1.1 + Math.sin(i / 2) * 0.35 + Math.cos(i / 5) * 0.12),
            latency: Math.round(38 + Math.sin(i / 3) * 9 + Math.cos(i / 1.4) * 4),
        });
    }
    return data;
}

// ---------- components ----------

function StatusBadge({ status, tone }: { status: string; tone: string }) {
    const map: Record<string, string> = {
        emerald: "bg-emerald-500/10 text-emerald-500",
        zinc: "bg-zinc-800 text-zinc-500",
        brand: "bg-brand/10 text-brand",
    };
    return (
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${map[tone]}`}>
            {status}
        </span>
    );
}

function RangePicker({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
    return (
        <div className="inline-flex items-center rounded-lg border border-zinc-800 bg-zinc-900/40 p-0.5">
            {RANGES.map((r) => (
                <button
                    key={r}
                    onClick={() => onChange(r)}
                    className={`px-3 py-1 text-[10px] font-mono uppercase tracking-wider rounded-md transition-colors ${value === r
                        ? "bg-red-500 text-zinc-950"
                        : "text-zinc-500 hover:text-zinc-300"
                        }`}
                >
                    {r}
                </button>
            ))}
        </div>
    );
}

function ChartTooltip({ active, payload, label, unit }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-md border border-zinc-800 bg-zinc-950/95 px-3 py-2 text-[11px] font-mono shadow-xl">
            <div className="text-zinc-500 uppercase tracking-wider text-[9px] mb-1">{label}</div>
            {payload.map((p: any) => (
                <div key={p.dataKey} className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full" style={{ background: p.color }} />
                    <span className="text-zinc-200">
                        {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
                        {unit}
                    </span>
                </div>
            ))}
        </div>
    );
}

function PoolDetailSheet({ pool, onClose }: { pool: Pool | null; onClose: () => void }) {
    const t = useT();

    return (
        <Sheet open={!!pool} onOpenChange={(o) => !o && onClose()}>
            <SheetContent
                side="right"
                className="w-full sm:max-w-md bg-zinc-950 border-l border-zinc-900 text-zinc-300 p-0 overflow-y-auto"
            >
                {pool && (
                    <>
                        <SheetHeader className="px-6 py-5 border-b border-zinc-900 text-left">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-500">
                                    {t.poolDetail}
                                </span>
                                <button
                                    onClick={onClose}
                                    className="size-7 grid place-items-center rounded-md hover:bg-zinc-900 text-zinc-500"
                                    aria-label="Close"
                                >
                                    <X className="size-4" />
                                </button>
                            </div>
                            <SheetTitle className="text-zinc-100 text-xl font-medium tracking-tight">
                                {pool.pair}
                            </SheetTitle>
                            <SheetDescription className="text-xs text-zinc-500 font-mono">
                                {pool.protocol} · Fee {pool.fee}
                            </SheetDescription>
                            <div className="pt-2">
                                <StatusBadge status={pool.status} tone={pool.tone} />
                            </div>
                        </SheetHeader>

                        <div className="px-6 py-5 space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
                                        APY
                                    </div>
                                    <div className="text-2xl font-mono text-emerald-400">{pool.apy}</div>
                                </div>
                                <div className="rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
                                        TVL
                                    </div>
                                    <div className="text-2xl font-mono text-zinc-100">{pool.tvl}</div>
                                </div>
                                <div className="rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
                                        {t.position}
                                    </div>
                                    <div className="text-sm font-mono text-zinc-200">{pool.position}</div>
                                </div>
                                <div className="rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
                                        {t.rewards24h}
                                    </div>
                                    <div className="text-sm font-mono text-emerald-400">{pool.rewards24h}</div>
                                </div>
                            </div>

                            <div>
                                <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-3">
                                    {t.apyLast24h}
                                </div>
                                <div className="h-32 rounded-lg border border-zinc-900 bg-zinc-900/20 p-2">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart
                                            data={Array.from({ length: 24 }, (_, i) => ({
                                                i,
                                                v: pool.apyNum + Math.sin(i / 2.1) * 1.2 + Math.cos(i / 1.3) * 0.6,
                                            }))}
                                        >
                                            <defs>
                                                <linearGradient id="pa" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="0%" stopColor="#ff2d2d" stopOpacity={0.4} />
                                                    <stop offset="100%" stopColor="#ff2d2d" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <Area
                                                type="monotone"
                                                dataKey="v"
                                                stroke="#ff2d2d"
                                                strokeWidth={1.5}
                                                fill="url(#pa)"
                                            />
                                            <Tooltip content={<ChartTooltip unit="%" />} />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div>
                                <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">
                                    {t.agentReasoning}
                                </div>
                                <p className="text-sm text-zinc-300 leading-relaxed text-pretty">
                                    {pool.reasoning}
                                </p>
                            </div>

                            <div className="rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                                <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">
                                    {t.riskProfile}
                                </div>
                                <div className="space-y-2 text-xs font-mono">
                                    <div className="flex justify-between">
                                        <span className="text-zinc-500">{t.impermanentLoss}</span>
                                        <span className="text-zinc-200">{pool.impermanentLoss}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-zinc-500">{t.scRisk}</span>
                                        <span className="text-emerald-400">{t.audited}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-zinc-500">{t.oracleSource}</span>
                                        <span className="text-zinc-200">CSPR.trade MCP</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-2 pb-4">
                                <button className="flex-1 py-2 px-3 bg-brand text-zinc-950 text-sm font-semibold rounded-lg hover:opacity-90 transition-opacity">
                                    {t.forceEntry}
                                </button>
                                <button className="flex-1 py-2 px-3 border border-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-900 transition-colors">
                                    {t.blacklist}
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </SheetContent>
        </Sheet>
    );
}

function DecisionRow({ d }: { d: Decision }) {
    const [open, setOpen] = useState(false);
    const t = useT();
    const ringColor =
        d.tone === "brand"
            ? "border-brand"
            : d.tone === "emerald"
                ? "border-emerald-500/50"
                : "border-zinc-800";
    const dotColor =
        d.tone === "brand" ? "bg-brand" : d.tone === "emerald" ? "bg-emerald-500" : "bg-zinc-800";
    const whenColor =
        d.tone === "brand"
            ? "text-brand"
            : d.tone === "emerald"
                ? "text-emerald-500/70"
                : "text-zinc-500";
    const statusMap = {
        Success: "bg-emerald-500/10 text-emerald-500",
        Pending: "bg-brand/10 text-brand",
        Observation: "bg-zinc-800 text-zinc-400",
    } as const;

    return (
        <Collapsible open={open} onOpenChange={setOpen}>
            <div className="relative pl-8">
                <div
                    className={`absolute left-0 top-1 size-6 rounded-full bg-zinc-950 border-2 ${ringColor} flex items-center justify-center`}
                >
                    <div className={`size-1.5 rounded-full ${dotColor}`} />
                </div>
                <CollapsibleTrigger className="w-full text-left group">
                    <div className="flex justify-between items-start mb-1 gap-3">
                        <span className={`text-xs font-mono ${whenColor}`}>{d.when}</span>
                        <div className="flex items-center gap-2">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${statusMap[d.status]}`}>
                                {d.status}
                            </span>
                            <span className="text-[10px] font-mono text-zinc-600">{d.tx}</span>
                            {open ? (
                                <ChevronDown className="size-3.5 text-zinc-500" />
                            ) : (
                                <ChevronRight className="size-3.5 text-zinc-500" />
                            )}
                        </div>
                    </div>
                    <div className="text-sm text-zinc-200 font-medium mb-1">{d.title}</div>
                    <p className="text-xs text-zinc-500 text-pretty leading-relaxed">{d.text}</p>
                </CollapsibleTrigger>

                <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                    <div className="mt-4 space-y-4 rounded-lg border border-zinc-900 bg-zinc-900/30 p-4">
                        <div>
                            <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 mb-2">
                                {t.inputs}
                            </div>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs font-mono">
                                {d.inputs.map((i) => (
                                    <div key={i.label} className="flex justify-between">
                                        <span className="text-zinc-500">{i.label}</span>
                                        <span className="text-zinc-200">{i.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div>
                            <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 mb-2">
                                {t.reasoningTrace}
                            </div>
                            <ul className="space-y-1.5">
                                {d.reasoning.map((r, idx) => (
                                    <li key={idx} className="text-xs text-zinc-400 flex gap-2">
                                        <span className="text-brand font-mono">›</span>
                                        <span className="text-pretty">{r}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="pt-2 border-t border-zinc-900 flex items-center justify-between">
                            <span className="text-[10px] font-mono text-zinc-600 truncate max-w-[60%]" title={d.deployHash}>
                                {d.deployHash.slice(0, 18)}…
                            </span>
                            <a
                                href={`${EXPLORER}${d.deployHash}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[10px] font-mono uppercase tracking-wider text-brand hover:underline flex items-center gap-1"
                            >
                                {t.viewExplorer} <ExternalLink className="size-3" />
                            </a>
                        </div>
                    </div>
                </CollapsibleContent>
            </div>
        </Collapsible>
    );
}

// ---------- main ----------

export const Dashboard = () => {
    const { sendNativeTransfer } = useCasperTransaction();
    const [actionAmount, setActionAmount] = useState<string>("50"); // valor por defecto
    const { status, loading } = useAgentStatus();

    const [selectedPool, setSelectedPool] = useState<Pool | null>(null);
    const [range, setRange] = useState<Range>("24H");
    const series = useMemo(() => buildSeries(range), [range]);
    const [slide, setSlide] = useState(0);
    // const [walletConnected, setWalletConnected] = useState(false);
    // const [walletAddress, setWalletAddress] = useState("");

    // const disconnectWallet = async () => {
    //     try {
    //         const providerFactory = (window as any).CasperWalletProvider;

    //         if (providerFactory) {
    //             const provider =
    //                 typeof providerFactory === "function"
    //                     ? providerFactory(window)
    //                     : providerFactory;

    //             if (provider.disconnect) {
    //                 await provider.disconnect();
    //             }

    //             if (provider.requestDisconnect) {
    //                 await provider.requestDisconnect();
    //             }
    //         }
    //     } catch (err) {
    //         console.error(err);
    //     }

    //     setWalletConnected(false);
    //     setWalletAddress("");
    // };
    const { connected: walletConnected, address: walletAddress, connect, disconnect: disconnectWallet } = useAgentWallet();
    const [nextCycle, setNextCycle] = useState(42);
    const [lang, setLang] = useState<Lang>("en");
    const t = dict[lang];
    const decisions: Decision[] = useMemo(() => {
        if (status?.decision_history && status.decision_history.length > 0) {
            return status.decision_history.slice(0, 5).map((d: any, index: number) => ({
                id: `dh${index}`,
                when: index === 0 ? "Just now" : `${index * 14} min ago`,
                tx: d.deploy_hash ? d.deploy_hash.slice(0, 8) + "..." : "—",
                deployHash: d.deploy_hash || "pending",
                title: d.action || "HOLD",
                text: d.reasoning || "Decisión del agente",
                tone: (d.action === "HOLD" ? "zinc" : "brand") as Decision["tone"],
                status: (d.deploy_hash ? "Success" : "Observation") as Decision["status"],
                inputs: [
                    { label: "Action", value: d.action || "HOLD" },
                    { label: "Timestamp", value: new Date(d.timestamp).toLocaleTimeString() },
                ],
                reasoning: [d.reasoning || "Monitoreo continuo del pool CSPR/sCSPR"],
            }));
        }
        return [{
            id: "no-decision",
            when: "Just now",
            tx: "—",
            deployHash: "—",
            title: "HOLD",
            text: "El agente está monitoreando el mercado.",
            tone: "zinc" as Decision["tone"],
            status: "Observation" as Decision["status"],
            inputs: [],
            reasoning: ["Esperando señal de APY superior al umbral."],
        }];
    }, [status]);
    const executeAction = async (actionType: string) => {
        if (!walletConnected || !walletAddress) {
            alert("Conecta tu wallet primero");
            return;
        }

        const amount = parseFloat(actionAmount);
        if (!amount || amount <= 0) {
            alert("Ingresa un monto válido mayor a 0");
            return;
        }

        const amountMotes = Math.floor(amount * 1_000_000_000).toString();

        try {
            const providerFactory = (window as any).CasperWalletProvider;
            const walletProvider = typeof providerFactory === "function"
                ? providerFactory(window)
                : providerFactory;

            if (!walletProvider) {
                throw new Error("Casper Wallet no detectada");
            }

            const deployHash = await sendNativeTransfer(
                walletAddress,
                walletAddress,        // ← Transfer a ti mismo (seguro para pruebas)
                amountMotes,
                walletProvider
            );

            alert(`✅ Transacción enviada exitosamente!\n\nHash:\n${deployHash}`);

            // Abrir explorer
            window.open(`${EXPLORER}${deployHash}`, "_blank");

        } catch (error: any) {
            console.error("Transaction error:", error);
            alert("❌ Error al enviar transacción:\n" + (error.message || error));
        }
    };
    useEffect(() => {
        const id = setInterval(() => {
            setNextCycle((s) => (s <= 1 ? 60 : s - 1));
        }, 1000);
        return () => clearInterval(id);
    }, []);


    return (
        <LangContext.Provider value={{ lang, t }}>
            <div className="min-h-screen bg-zinc-950 text-zinc-300 font-sans selection:bg-brand/30 pb-16">
                <nav className="sticky top-0 z-50 border-b border-red-500/20 bg-black/90 backdrop-blur-md">
                    <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-3">
                                <div className="neon-glow flex h-9 w-9 items-center justify-center rounded-xl bg-red-500 text-black">
                                    <Zap className="h-5 w-5" />
                                </div>
                                <span className="font-mono text-xl font-bold tracking-tighter neon-text-red">YIELDAGENT</span>
                            </div>

                            {walletConnected && (
                                <div className="hidden md:flex items-center gap-6 ml-6">
                                    <Link
                                        to="/agent"
                                        className="text-sm font-mono uppercase tracking-wider text-red-400 hover:text-red-300 transition-colors neon-text-red"
                                    >
                                        Agent
                                    </Link>
                                    <Link
                                        to="/audit"
                                        className="text-sm font-mono uppercase tracking-wider text-red-400 hover:text-red-300 transition-colors neon-text-red"
                                    >
                                        Audit Logs
                                    </Link>
                                </div>
                            )}

                            <div className="h-4 w-px bg-red-500/20 mx-2 hidden md:block" />
                            <div className="hidden sm:flex items-center gap-2">
                                <div className="size-2 rounded-full bg-emerald-500 animate-pulse-soft" />
                                <span className="text-xs font-mono uppercase tracking-wider text-emerald-500/80">
                                    {t.agentActive}
                                </span>
                            </div>
                            <div className="hidden lg:flex items-center gap-2 pl-3 ml-1 border-l border-red-500/20">
                                <span className="text-[10px] uppercase tracking-widest text-zinc-500">
                                    {t.nextCycle}
                                </span>
                                <span className="text-xs font-mono text-zinc-200 tabular-nums">
                                    {String(Math.floor(nextCycle / 60)).padStart(2, "0")}:
                                    {String(nextCycle % 60).padStart(2, "0")}
                                </span>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="hidden md:flex flex-col items-end">
                                <span className="text-[10px] uppercase tracking-widest text-zinc-500 font-medium">
                                    {t.testnetNode}
                                </span>
                                <span className="text-xs font-mono text-zinc-300">casper-test-03</span>
                            </div>
                            <div className="inline-flex items-center rounded-lg border border-red-500/30 bg-zinc-900/40 p-0.5">
                                {(["en", "es"] as const).map((l) => (
                                    <button
                                        key={l}
                                        onClick={() => setLang(l)}
                                        className={`px-2 py-1 text-[10px] font-mono uppercase tracking-wider rounded-md transition-colors ${lang === l ? "bg-red-500 text-zinc-950" : "text-zinc-500 hover:text-zinc-300"
                                            }`}
                                        aria-pressed={lang === l}
                                    >
                                        {l}
                                    </button>
                                ))}
                            </div>
                            <div className="flex items-center gap-4">
                                {walletConnected ? (
                                    <ProfileMenu
                                        walletAddress={walletAddress}
                                        onDisconnect={disconnectWallet}
                                    />
                                ) : null}
                            </div>
                        </div>
                    </div>
                </nav>
                {/* Contenido principal condicional */}
                {!walletConnected ? (
                    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center px-6">
                        <div className="max-w-md text-center">
                            <div className="mx-auto size-20 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-8">
                                <Wallet className="size-10 text-zinc-500" />
                            </div>
                            <h2 className="text-3xl font-semibold text-zinc-100 mb-3">Conecta tu Wallet</h2>
                            <p className="text-zinc-400 mb-8 text-lg">
                                Es necesario conectar una wallet de Casper para acceder al dashboard del agente autónomo.
                            </p>
                            <WalletConnect
                                connectWallet={t.connectWallet}
                                onConnected={connect}
                            />
                        </div>
                    </div>
                ) :
                    (
                        <main className="mx-auto max-w-7xl px-6 py-10">
                            <h1 className="sr-only">Casper Autopilot Dashboard</h1>

                            {/* Hero */}
                            <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                                <div className="md:col-span-2 p-6 rounded-xl bg-zinc-900/50 border border-zinc-800 flex flex-col justify-between">
                                    <div className="flex items-start justify-between gap-4">
                                        <div>
                                            <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-4">
                                                Total Vault Balance
                                            </h2>
                                            <div className="flex items-baseline gap-3">
                                                <span className="text-5xl font-medium text-zinc-100 tracking-tight leading-none tabular-nums">
                                                    {status?.balance_cspr ? status.balance_cspr.toLocaleString() : "0"}
                                                </span>
                                                <span className="text-xl font-mono text-brand">CSPR</span>
                                            </div>
                                            <p className="mt-2 text-sm text-zinc-500 font-mono">
                                                ≈ ${status?.balance_cspr ? (status.balance_cspr * 0.034).toFixed(2) : "0.00"} USD
                                            </p>
                                        </div>
                                        <RangePicker value={range} onChange={setRange} />
                                    </div>

                                    <div className="mt-6 h-40">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={series} margin={{ top: 10, right: 4, left: -16, bottom: 0 }}>
                                                <defs>
                                                    <linearGradient id="bal" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="0%" stopColor="#ff2d2d" stopOpacity={0.45} />
                                                        <stop offset="100%" stopColor="#ff2d2d" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid stroke="#18181b" vertical={false} />
                                                <XAxis
                                                    dataKey="label"
                                                    stroke="#52525b"
                                                    tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                                                    tickLine={false}
                                                    axisLine={false}
                                                    interval="preserveStartEnd"
                                                />
                                                <YAxis
                                                    stroke="#52525b"
                                                    tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                                                    tickLine={false}
                                                    axisLine={false}
                                                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                                                    width={48}
                                                />
                                                <Tooltip content={<ChartTooltip unit=" CSPR" />} cursor={{ stroke: "#3f3f46" }} />
                                                <Area
                                                    type="monotone"
                                                    dataKey="balance"
                                                    stroke="#ff2d2d"
                                                    strokeWidth={1.8}
                                                    fill="url(#bal)"
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>

                                    <div className="mt-4 flex gap-8 border-t border-zinc-800 pt-5">
                                        <div>
                                            <span className="block text-[10px] uppercase text-zinc-500 mb-1">{range} {t.rangeChange}</span>
                                            <span className="text-sm font-mono text-emerald-400">+0.0%</span>
                                        </div>
                                        <div>
                                            <span className="block text-[10px] uppercase text-zinc-500 mb-1">{t.activePositions}</span>
                                            <span className="text-sm font-mono text-zinc-200">1</span>
                                        </div>
                                        <div>
                                            <span className="block text-[10px] uppercase text-zinc-500 mb-1">{t.totalDeploys}</span>
                                            <span className="text-sm font-mono text-zinc-200">
                                                {status?.actions_taken ?? "0"}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-3">
                                    {/* Dots */}
                                    <div className="flex justify-center gap-2">
                                        {[0, 1].map((i) => (
                                            <button
                                                key={i}
                                                onClick={() => setSlide(i)}
                                                className={`size-1.5 rounded-full transition-all duration-200 ${slide === i ? "bg-brand scale-150" : "bg-zinc-700"
                                                    }`}
                                            />
                                        ))}
                                    </div>

                                    {/* Track */}
                                    <div className="overflow-hidden rounded-xl">
                                        <div
                                            className="flex transition-transform duration-300 ease-in-out"
                                            style={{ transform: `translateX(-${slide * 100}%)` }}
                                        >
                                            {/* SLIDE 0 — Agent Status */}
                                            <div className="min-w-full p-6 rounded-xl bg-red-500/5 border border-red-500/40 shadow-[0_0_20px_rgba(255,45,45,0.25)]">

                                                {/* Agent active pill */}
                                                <div className="flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/5 p-4 mb-5">
                                                    <Bot
                                                        className="size-10 text-green-400"
                                                        style={{ filter: "drop-shadow(0 0 6px #22c55e) drop-shadow(0 0 12px #22c55e)" }}
                                                    />
                                                    <div className="flex flex-col gap-0.5">
                                                        <span
                                                            className="font-mono text-green-400 uppercase tracking-[0.2em] text-sm"
                                                            style={{ textShadow: "0 0 5px #22c55e, 0 0 10px #22c55e, 0 0 20px #22c55e" }}
                                                        >
                                                            {loading ? "LOADING..." : status?.status === "running" ? "AGENT IS ACTIVE" : "AGENT STOPPED"}
                                                        </span>
                                                        {status?.last_updated && (
                                                            <span className="text-[9px] font-mono text-green-500/50 uppercase tracking-widest">
                                                                Updated {new Date(status.last_updated).toLocaleTimeString()}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Title */}
                                                <h2
                                                    className="text-xs font-medium uppercase tracking-widest text-red-400 mb-4"
                                                    style={{ textShadow: "0 0 5px #ff2d2d, 0 0 10px #ff2d2d" }}
                                                >
                                                    {t.agentStrategy}
                                                </h2>

                                                {/* Stats grid */}
                                                <div className="grid grid-cols-2 gap-2 mb-4">
                                                    {[
                                                        {
                                                            label: "Balance",
                                                            value: status?.balance_cspr != null ? `${status.balance_cspr.toLocaleString()} CSPR` : "—",
                                                            color: "text-zinc-200",
                                                        },
                                                        {
                                                            label: t.totalDeploys,
                                                            value: status?.actions_taken != null ? String(status.actions_taken) : "—",
                                                            color: "text-zinc-200",
                                                        },
                                                        {
                                                            label: "Pool APY",
                                                            value: status?.last_market_data?.pool_apy != null ? `${status.last_market_data.pool_apy.toFixed(2)}%` : "—",
                                                            color: "text-emerald-400",
                                                        },
                                                        {
                                                            label: t.nextCycle,
                                                            value: `${String(Math.floor(nextCycle / 60)).padStart(2, "0")}:${String(nextCycle % 60).padStart(2, "0")}`,
                                                            color: "text-red-400",
                                                        },
                                                    ].map(({ label, value, color }) => (
                                                        <div key={label} className="rounded-lg border border-red-500/15 bg-red-500/5 p-3">
                                                            <div className="text-[9px] uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
                                                            <div className={`text-sm font-mono font-semibold ${color}`}>{value}</div>
                                                        </div>
                                                    ))}
                                                </div>

                                                {/* APY threshold row */}
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="text-sm text-zinc-300">{t.apyThreshold}</span>
                                                    <span
                                                        className="text-sm font-mono text-red-400"
                                                        style={{ textShadow: "0 0 5px #ff2d2d, 0 0 10px #ff2d2d" }}
                                                    >
                                                        &gt;12.5%
                                                    </span>
                                                </div>

                                                {/* Progress bar — current APY vs threshold */}
                                                <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden mb-1">
                                                    <div
                                                        className="h-full bg-green-400 rounded-full transition-all duration-500"
                                                        style={{
                                                            width: status?.last_market_data?.pool_apy
                                                                ? `${Math.min((status.last_market_data.pool_apy / 25) * 100, 100).toFixed(0)}%`
                                                                : "0%",
                                                        }}
                                                    />
                                                </div>
                                                <div className="text-[10px] text-zinc-600 text-right font-mono mb-3">
                                                    Current APY {status?.last_market_data?.current_apy?.toFixed(2) ?? "—"}%
                                                </div>

                                                {/* Last decision box */}
                                                {status?.last_decision && (
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 mb-4">
                                                        <div className="text-[9px] uppercase tracking-widest text-zinc-500 mb-2">Last decision</div>
                                                        <div className="flex items-center justify-between mb-1.5">
                                                            <span className="text-xs font-mono font-semibold text-zinc-100">
                                                                {status.last_decision.action}
                                                            </span>
                                                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${status.last_decision.action === "HOLD"
                                                                ? "bg-zinc-800 text-zinc-400"
                                                                : status.last_decision.action === "SWAP"
                                                                    ? "bg-brand/10 text-brand"
                                                                    : "bg-emerald-500/10 text-emerald-500"
                                                                }`}>
                                                                {status.last_decision.action}
                                                            </span>
                                                        </div>
                                                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                                                            {status.last_decision.reasoning}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Swarm Panel */}
                                                {status?.last_swarm_result && (
                                                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 mb-4">
                                                        <div className="text-[9px] uppercase tracking-widest text-zinc-500 mb-2">
                                                            Swarm ·{" "}
                                                            <span className={status.last_swarm_result.final_action === "SWAP"
                                                                ? "text-brand font-bold"
                                                                : "text-zinc-400 font-bold"
                                                            }>
                                                                {status.last_swarm_result.vote_tally["SWAP"] ?? 0} SWAP
                                                                {" / "}
                                                                {status.last_swarm_result.vote_tally["HOLD"] ?? 0} HOLD
                                                                {" → "}
                                                                {status.last_swarm_result.final_action}
                                                            </span>
                                                        </div>
                                                        <div className="space-y-2">
                                                            {status.last_swarm_result.votes.map((vote: any) => (
                                                                <div key={vote.agent_name} className="flex items-start gap-2">
                                                                    <span className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase mt-0.5 ${vote.action === "SWAP"
                                                                        ? "bg-brand/10 text-brand"
                                                                        : "bg-zinc-800 text-zinc-400"
                                                                        }`}>
                                                                        {vote.action}
                                                                    </span>
                                                                    <div>
                                                                        <div className="text-[9px] font-mono text-zinc-500 uppercase tracking-wide">
                                                                            {vote.agent_name.replace(/_/g, " ")}
                                                                        </div>
                                                                        <p className="text-[10px] text-zinc-400 leading-relaxed">
                                                                            {vote.reasoning}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Errors */}
                                                {status?.errors?.length > 0 && (
                                                    <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 mb-4">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <div className="text-[9px] uppercase tracking-widest text-red-400">
                                                                Errors ({status.errors.length})
                                                            </div>
                                                            <div className="size-1.5 rounded-full bg-red-500 animate-pulse" />
                                                        </div>
                                                        <div className="max-h-16 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-red-500/20 scrollbar-track-transparent pr-1">
                                                            {status.errors.map((e: string, i: number) => (
                                                                <p
                                                                    key={i}
                                                                    className="text-[10px] text-red-300/70 font-mono leading-relaxed truncate"
                                                                    title={e}
                                                                >
                                                                    › {e.length > 48 ? e.slice(0, 48) + "…" : e}
                                                                </p>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Button */}
                                                <button
                                                    className="w-full py-2 px-3 rounded-lg text-sm font-semibold text-white border border-red-500/60 bg-red-500/10 hover:bg-red-500/20 transition-all shadow-[0_0_15px_rgba(255,45,45,0.35)]"
                                                    style={{ textShadow: "0 0 5px #ff2d2d, 0 0 10px #ff2d2d" }}
                                                >
                                                    {t.updateStrategy}
                                                </button>
                                            </div>

                                            {/* SLIDE 1 — Vault Actions */}
                                            <div className="min-w-full p-6 rounded-xl bg-indigo-500/5 border border-indigo-500/30">
                                                {/* Balance */}
                                                <div className="flex items-center gap-3 mb-5">
                                                    <div className="size-10 rounded-lg bg-indigo-500/10 border border-indigo-500/25 grid place-items-center">
                                                        <Vault className="size-5 text-indigo-400" />
                                                    </div>
                                                    <div>
                                                        <h3 className="font-semibold text-indigo-400 uppercase tracking-wider text-sm">
                                                            Vault actions
                                                        </h3>
                                                        <p className="text-[10px] text-zinc-500 uppercase tracking-wider">
                                                            Execute manual operations
                                                        </p>
                                                    </div>
                                                </div>

                                                {/* Balance box */}
                                                {/* Balance box */}
                                                <div className="rounded-lg border border-indigo-500/15 bg-indigo-500/5 p-3 mb-4">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <div>
                                                            <div className="text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
                                                                Total vault balance
                                                            </div>
                                                            <div className="text-xl font-mono text-zinc-100">
                                                                {status?.balance_cspr ? status.balance_cspr.toLocaleString() : "0"}{" "}
                                                                <span className="text-sm text-indigo-400">CSPR</span>
                                                            </div>
                                                            <div className="text-[10px] text-zinc-500 mt-0.5">
                                                                ≈ ${status?.balance_cspr ? (status.balance_cspr * 0.034).toFixed(2) : "0.00"} USD
                                                            </div>
                                                        </div>
                                                        <span className="text-[9px] px-2 py-1 rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 uppercase tracking-widest">
                                                            Testnet
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* Stats */}
                                                <div className="grid grid-cols-3 gap-1.5 mb-4">
                                                    {[
                                                        { l: "Staked", v: "184,200", c: "text-emerald-400" },
                                                        { l: "Rewards 24h", v: "+42.18", c: "text-emerald-400" },
                                                        { l: "Gas price", v: "1.2 gwei", c: "text-zinc-200" },
                                                    ].map(({ l, v, c }) => (
                                                        <div key={l} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-center">
                                                            <div className="text-[9px] uppercase tracking-widest text-zinc-500 mb-1">{l}</div>
                                                            <div className={`text-xs font-mono ${c}`}>{v}</div>
                                                        </div>
                                                    ))}
                                                </div>

                                                <div className="space-y-4">
                                                    {/* Amount Input */}
                                                    <div>
                                                        <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">Amount (CSPR)</div>
                                                        <input
                                                            type="number"
                                                            value={actionAmount}
                                                            onChange={(e) => setActionAmount(e.target.value)}
                                                            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3 text-zinc-100 focus:border-indigo-500 outline-none text-lg font-mono"
                                                            placeholder="50.0"
                                                        />
                                                    </div>

                                                    {/* Action Buttons */}
                                                    <div className="grid grid-cols-2 gap-3">
                                                        {[
                                                            { label: "Deposit", action: "deposit", color: "indigo" },
                                                            { label: "Withdraw", action: "withdraw", color: "zinc" },
                                                            { label: "Stake", action: "stake", color: "emerald" },
                                                            { label: "Swap", action: "swap", color: "brand" },
                                                        ].map(({ label, action, color }) => (
                                                            <button
                                                                key={action}
                                                                onClick={() => executeAction(action)}
                                                                className={`py-3 px-4 rounded-xl border text-sm font-semibold transition-all hover:scale-[1.02] ${color === "indigo"
                                                                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20"
                                                                    : color === "emerald"
                                                                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                                                                        : color === "brand"
                                                                            ? "border-brand bg-brand/10 text-brand hover:bg-brand/20"
                                                                            : "border-zinc-700 bg-zinc-900 text-zinc-400 hover:bg-zinc-800"
                                                                    }`}
                                                            >
                                                                {label}
                                                            </button>
                                                        ))}
                                                    </div>

                                                    <button
                                                        onClick={() => executeAction("execute")}
                                                        className="flex items-center justify-center gap-2 w-full py-3.5 rounded-xl border border-indigo-500/50 bg-indigo-500/10 text-indigo-400 font-semibold text-base hover:bg-indigo-500/20 transition-all"
                                                    >
                                                        <Send size={18} />
                                                        Execute Transaction
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Nav buttons */}
                                    <div className="flex justify-center gap-2">
                                        <button
                                            onClick={() => setSlide(0)}
                                            className="size-8 rounded-md border border-zinc-800 bg-zinc-900 text-zinc-500 hover:border-brand hover:text-brand transition-colors grid place-items-center"
                                        >
                                            <ChevronLeft className="size-4" />
                                        </button>
                                        <button
                                            onClick={() => setSlide(1)}
                                            className="size-8 rounded-md border border-zinc-800 bg-zinc-900 text-zinc-500 hover:border-brand hover:text-brand transition-colors grid place-items-center"
                                        >
                                            <ChevronRight className="size-4" />
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* On-chain telemetry trends */}
                            <section className="mb-12">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h3 className="text-sm font-medium text-zinc-100">{t.onchainTelemetry}</h3>
                                        <p className="text-[10px] font-mono text-zinc-500 mt-0.5">
                                            {t.telemetrySub} · {range} {t.window}
                                        </p>
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="rounded-xl border border-zinc-900 bg-zinc-900/30 p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-[10px] uppercase tracking-widest text-zinc-500">
                                                {t.gasPrice}
                                            </span>
                                            <span className="text-xs font-mono text-zinc-200">1.2 gwei</span>
                                        </div>
                                        <div className="h-28">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={series} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
                                                    <CartesianGrid stroke="#18181b" vertical={false} />
                                                    <XAxis
                                                        dataKey="label"
                                                        stroke="#52525b"
                                                        tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }}
                                                        tickLine={false}
                                                        axisLine={false}
                                                        interval="preserveStartEnd"
                                                    />
                                                    <YAxis
                                                        stroke="#52525b"
                                                        tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }}
                                                        tickLine={false}
                                                        axisLine={false}
                                                        width={36}
                                                    />
                                                    <Tooltip content={<ChartTooltip unit=" gwei" />} cursor={{ stroke: "#3f3f46" }} />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="gas"
                                                        stroke="#10b981"
                                                        strokeWidth={1.5}
                                                        dot={false}
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    <div className="rounded-xl border border-zinc-900 bg-zinc-900/30 p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-[10px] uppercase tracking-widest text-zinc-500">
                                                {t.nodeLatency}
                                            </span>
                                            <span className="text-xs font-mono text-zinc-200">42 ms</span>
                                        </div>
                                        <div className="h-28">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={series} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
                                                    <CartesianGrid stroke="#18181b" vertical={false} />
                                                    <XAxis
                                                        dataKey="label"
                                                        stroke="#52525b"
                                                        tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }}
                                                        tickLine={false}
                                                        axisLine={false}
                                                        interval="preserveStartEnd"
                                                    />
                                                    <YAxis
                                                        stroke="#52525b"
                                                        tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }}
                                                        tickLine={false}
                                                        axisLine={false}
                                                        width={36}
                                                    />
                                                    <Tooltip content={<ChartTooltip unit=" ms" />} cursor={{ stroke: "#3f3f46" }} />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="latency"
                                                        stroke="#ff2d2d"
                                                        strokeWidth={1.5}
                                                        dot={false}
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* Scanner + Decisions */}
                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                                <div className="lg:col-span-7 space-y-6">
                                    <div className="flex items-center justify-between mb-2">
                                        <h3 className="text-sm font-medium text-zinc-100">{t.opportunityScanner}</h3>
                                        <span className="text-[10px] font-mono text-zinc-500">{t.clickPool}</span>
                                    </div>

                                    <div className="overflow-hidden rounded-xl border border-zinc-900 bg-zinc-950">
                                        <table className="w-full text-left text-sm">
                                            <thead>
                                                <tr className="border-b border-zinc-900 bg-zinc-900/30">
                                                    <th className="px-4 py-3 font-medium text-zinc-500 text-xs uppercase">{t.poolName}</th>
                                                    <th className="px-4 py-3 font-medium text-zinc-500 text-xs uppercase">APY</th>
                                                    <th className="px-4 py-3 font-medium text-zinc-500 text-xs uppercase">TVL</th>
                                                    <th className="px-4 py-3 font-medium text-zinc-500 text-xs uppercase text-right">
                                                        {t.status}
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-zinc-900/50">
                                                {pools.map((p) => (
                                                    <tr
                                                        key={p.pair}
                                                        onClick={() => setSelectedPool(p)}
                                                        className={`cursor-pointer transition-colors ${selectedPool?.pair === p.pair
                                                            ? "bg-zinc-900/60"
                                                            : "hover:bg-zinc-900/40"
                                                            }`}
                                                    >
                                                        <td className="px-4 py-4 font-medium text-zinc-200">{p.pair}</td>
                                                        <td
                                                            className={`px-4 py-4 font-mono ${p.muted ? "text-zinc-400" : "text-emerald-400"
                                                                }`}
                                                        >
                                                            {p.apy}
                                                        </td>
                                                        <td className="px-4 py-4 font-mono text-zinc-400 text-xs">{p.tvl}</td>
                                                        <td className="px-4 py-4 text-right">
                                                            <StatusBadge status={p.status} tone={p.tone} />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="p-4 rounded-xl bg-zinc-900/20 border border-zinc-900 flex items-center gap-4">
                                        <div className="shrink-0 size-8 rounded-full bg-zinc-800 flex items-center justify-center">
                                            <Info className="size-4 text-zinc-500" />
                                        </div>
                                        <p className="text-xs text-zinc-500 text-pretty">
                                            {t.scannerHint}
                                        </p>
                                    </div>
                                </div>

                                <div className="lg:col-span-5">
                                    <div className="flex items-center justify-between mb-6">
                                        <h3 className="text-sm font-medium text-zinc-100">{t.reasoningFeed}</h3>
                                        <span className="text-[10px] font-mono text-zinc-500">{t.expandDrill}</span>
                                    </div>

                                    <div className="space-y-6 relative">
                                        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-zinc-900" />
                                        {decisions.map((d) => (
                                            <DecisionRow key={d.id} d={d} />
                                        ))}
                                    </div>

                                    <button className="w-full mt-10 py-3 border border-zinc-900 text-xs font-medium uppercase tracking-widest text-zinc-500 rounded-lg hover:text-zinc-300 hover:border-zinc-700 transition-colors">
                                        {t.viewAudit}
                                    </button>
                                </div>
                            </div>
                            <footer className="fixed bottom-0 left-0 right-0 border-t border-zinc-900 bg-zinc-950/80 backdrop-blur-md z-30">
                                <div className="mx-auto max-w-7xl px-6 h-10 flex items-center justify-between text-[10px] font-mono text-zinc-600">
                                    <div className="flex gap-6">
                                        <span>
                                            LATENCY:{" "}
                                            <span className="text-zinc-400">
                                                {status?.last_market_data?.estimated_slippage != null
                                                    ? `${(status.last_market_data.estimated_slippage * 100).toFixed(2)}% slippage`
                                                    : "42ms"}
                                            </span>
                                        </span>
                                        <span>
                                            CSPR/USD:{" "}
                                            <span className="text-zinc-400">
                                                ${status?.last_market_data?.cspr_price_usd?.toFixed(5) ?? "—"}
                                            </span>
                                        </span>
                                        <span>
                                            BALANCE:{" "}
                                            <span className="text-zinc-400">
                                                {status?.balance_cspr != null ? `${status.balance_cspr.toLocaleString()} CSPR` : "—"}
                                            </span>
                                        </span>
                                    </div>
                                    <div className="flex gap-4">
                                        <span className={status?.status === "running" ? "text-emerald-500/60" : "text-red-500/60"}>
                                            {status?.status?.toUpperCase() ?? t.connected}
                                        </span>
                                        <span>v0.12.4-BETA</span>
                                    </div>
                                </div>
                            </footer>
                        </main>
                    )
                }


                <PoolDetailSheet pool={selectedPool} onClose={() => setSelectedPool(null)} />
            </div >
        </LangContext.Provider >
    );
}

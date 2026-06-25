import { useEffect, useState } from "react";
import { ArrowUpRight, Eye, Brain, Zap, FileText, Github } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAgentWallet } from "../context/AgentWalletContext";
import { WalletConnect } from "#components/WalletConnect";
import { ProfileMenu } from "#components/ProfileOptions";
import { useAgentStatus } from "#hooks/useAgentStatus";
import { useAgentConfig } from "#hooks/useAgentConfig";

type Lang = "en" | "es";

const dict = {
    en: {
        badge: "Casper Agentic Buildathon 2026 · Testnet live",
        heroLine1: "Your capital.",
        heroLine2: "The agent decides.",
        heroSub: "An autonomous AI agent that monitors DeFi pools on Casper Network, executes swaps when APY justifies it, and logs every decision on-chain.",
        ctaDashboard: "Open live dashboard",
        ctaExplorer: "Testnet explorer",
        loopTitle: "agent.py · main loop",
        observe: "Observe",
        decide: "Decide",
        execute: "Execute",
        log: "Log",
        stats: {
            decisions: "Decisions logged",
            uptime: "Loop uptime",
            avgApy: "Avg. APY delta",
            latency: "Avg. cycle",
        },
        agentStateTitle: "Agent state",
        running: "RUNNING",
        nextCycle: "Next cycle",
        balanceLabel: "Vault balance",
        networkLabel: "Network",
        ruleLabel: "APY rule",
        slippageLabel: "Max slippage",
        stack: "STACK",
        feedTitle: "Real-time decisions",
        howTitle: "How it works",
        howSub: "The autonomous loop",
        howDesc: "Every 5 minutes the agent runs this cycle without human intervention.",
        steps: [
            { t: "Observe", d: "Reads vault balance, CSPR/sCSPR prices and pool APY via Casper MCP and CSPR.trade MCP." },
            { t: "Decide", d: "Claude analyzes the conditions: if APY rises +2% and slippage < 1.5%, the verdict is SWAP. Otherwise HOLD." },
            { t: "Execute", d: "Signs and submits the transaction on-chain via CSPR.click." },
            { t: "Log", d: "Records the decision on-chain with log_action()." },
        ],
        featuresTitle: "Features",
        featuresSub: "Built for the buildathon",
        features: [
            { t: "Onchain audit", d: "Every decision is logged inside the YieldVault contract." },
            { t: "Casper-native", d: "Talks directly to the Casper blockchain using pycspr and Casper RPC. No MCP CallContract." },
            { t: "Claude reasoning", d: "Uses LLM reasoning to weigh APY, slippage and liquidity." },
            { t: "CSPR.click", d: "Wallet flow ready for jury demo." },
            { t: "Live dashboard", d: "Real-time visibility of every agent action." },
        ],
        roadmapTitle: "Roadmap",
        roadmapSub: "From testnet to production",
        roadmap: [
            { q: "Q2 2026", label: "NOW", items: ["YieldVault on Testnet", "Functional agent loop", "Live React dashboard"] },
            { q: "Q3 2026", label: "NEXT", items: ["Mainnet migration", "Multi-pool support", "Telegram alerts"] },
        ],
        ctaTitle: "Watch the agent in action",
        ctaDesc: "Every transaction is real and verifiable on Casper Testnet.",
        ctaViewTx: "View transactions",
        ctaSource: "Source code",
        connectWallet: "Connect wallet",
        footer: "Casper Agentic Buildathon 2026",
        nav: { how: "How it works", features: "Features", roadmap: "Roadmap" },
    },
    es: {
        badge: "Casper Agentic Buildathon 2026 · Testnet activo",
        heroLine1: "Tu capital.",
        heroLine2: "El agente decide.",
        heroSub: "Un agente de IA autónomo que monitorea pools DeFi en Casper Network, ejecuta swaps cuando el APY lo justifica y loguea cada decisión on-chain.",
        ctaDashboard: "Abrir dashboard en vivo",
        ctaExplorer: "Explorador testnet",
        loopTitle: "agent.py · loop principal",
        observe: "Observar",
        decide: "Decidir",
        execute: "Ejecutar",
        log: "Loguear",
        stats: {
            decisions: "Decisiones logueadas",
            uptime: "Uptime del loop",
            avgApy: "Δ APY promedio",
            latency: "Ciclo promedio",
        },
        agentStateTitle: "Estado del agente",
        running: "CORRIENDO",
        nextCycle: "Próximo ciclo",
        balanceLabel: "Balance del vault",
        networkLabel: "Red",
        ruleLabel: "Regla APY",
        slippageLabel: "Slippage máx.",
        stack: "STACK",
        feedTitle: "Decisiones en tiempo real",
        howTitle: "Cómo funciona",
        howSub: "El loop autónomo",
        howDesc: "Cada 5 minutos el agente ejecuta este ciclo sin intervención humana.",
        steps: [
            { t: "Observar", d: "Lee balance del vault, precios CSPR/sCSPR y APY del pool via Casper MCP y CSPR.trade MCP." },
            { t: "Decidir", d: "Claude analiza las condiciones: si el APY sube +2% y slippage < 1.5%, el veredicto es SWAP. Si no, HOLD." },
            { t: "Ejecutar", d: "Firma y envía la transacción on-chain via CSPR.click." },
            { t: "Loguear", d: "Registra la decisión on-chain con log_action()." },
        ],
        featuresTitle: "Características",
        featuresSub: "Construido para el buildathon",
        features: [
            { t: "Auditoría onchain", d: "Cada decisión se loguea dentro del contrato YieldVault. Totalmente trazable." },
            { t: "Casper-native", d: "Se comunica directamente con la blockchain de Casper usando pycspr y Casper RPC." },
            { t: "Razonamiento Claude", d: "Usa LLM para pesar APY, slippage y liquidez en cada paso." },
            { t: "CSPR.click", d: "Flujo de wallet listo para la demo del jurado con firma nativa Casper." },
            { t: "Dashboard en vivo", d: "Los operadores ven cada acción del agente con timestamps y tx hashes." },
        ],
        roadmapTitle: "Roadmap",
        roadmapSub: "De testnet a producción",
        roadmap: [
            { q: "Q2 2026", label: "ACTUAL", items: ["YieldVault en Testnet", "Loop agente funcional", "Dashboard React live", "Demo para el jurado"] },
            { q: "Q3 2026", label: "PRÓXIMO", items: ["Migración a Mainnet", "Soporte multi-pool", "Alertas Telegram/Discord", "Optimización de gas"] },
            { q: "Q4 2026", label: "FUTURO", items: ["API pública para dApps", "Múltiples estrategias", "Integración fiat on-ramp", "SDK para devs"] },
        ],
        ctaTitle: "Mirá el agente en acción",
        ctaDesc: "Cada transacción es real y verificable en Casper Testnet.",
        ctaViewTx: "Ver transacciones",
        ctaSource: "Ver código fuente",
        connectWallet: "Conectar wallet",
        footer: "Casper Agentic Buildathon 2026",
        nav: { how: "Cómo funciona", features: "Características", roadmap: "Roadmap" },
    },
} as const;

const LOOP_ICONS = [Eye, Brain, Zap, FileText];

function LoopTicker({ labels }: { labels: string[] }) {
    const [active, setActive] = useState(0);
    useEffect(() => {
        const t = setInterval(() => setActive((a) => (a + 1) % 4), 1600);
        return () => clearInterval(t);
    }, []);
    return (
        <div className="flex flex-wrap items-center justify-center gap-4">
            {labels.map((label, i) => {
                const Icon = LOOP_ICONS[i];
                const isActive = i === active;
                return (
                    <div key={i} className="flex items-center gap-3">
                        <div className={`neon-step flex items-center gap-2.5 rounded-full border px-6 py-3 font-mono text-sm uppercase tracking-wider transition-all duration-700 ${isActive ? 'neon-active' : ''}`}>
                            <Icon className="h-4 w-4" />
                            {label}
                        </div>
                        {i < 3 && <div className="h-px w-8 bg-red-500/30" />}
                    </div>
                );
            })}
        </div>
    );
}

export const LandingPage = () => {
    const { connected: walletConnected, address: walletAddress, connect, disconnect: disconnectWallet } = useAgentWallet();
    const navigate = useNavigate();
    const { status } = useAgentStatus();
    const config = useAgentConfig();

    const handleConnectAndRedirect = async () => {
        await connect();
        navigate("/dashboard");
    };

    const [lang, setLang] = useState<Lang>("es");
    const t = dict[lang];
    const [nextIn, setNextIn] = useState(config.check_interval_seconds);

    useEffect(() => {
        setNextIn(config.check_interval_seconds);
    }, [config.check_interval_seconds]);

    useEffect(() => {
        const i = setInterval(
            () => setNextIn((n) => (n <= 0 ? config.check_interval_seconds : n - 1)),
            1000,
        );
        return () => clearInterval(i);
    }, [config.check_interval_seconds]);

    const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-zinc-100 font-sans overflow-hidden">
            {/* Neon ambient background */}
            <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(at_50%_20%,rgba(255,45,45,0.12),transparent_70%)]" />

            {/* NAV */}
            <nav className="sticky top-0 z-50 border-b border-red-500/20 bg-black/90 backdrop-blur-md">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
                    <div className="flex items-center gap-3">
                        <div className="neon-glow flex h-9 w-9 items-center justify-center rounded-xl bg-red-500 text-black">
                            <Zap className="h-5 w-5" />
                        </div>
                        <span className="font-mono text-2xl font-bold tracking-tighter neon-text-red">YIELDAGENT</span>
                    </div>

                    <div className="hidden items-center gap-8 text-sm md:flex">
                        <a href="#how" className="hover:text-red-400 transition-colors">{t.nav.how}</a>
                        <a href="#features" className="hover:text-red-400 transition-colors">{t.nav.features}</a>
                        <a href="#roadmap" className="hover:text-red-400 transition-colors">{t.nav.roadmap}</a>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="inline-flex items-center rounded-lg border border-red-500/30 bg-zinc-900/40 p-0.5">
                            {(["en", "es"] as const).map((l) => (
                                <button
                                    key={l}
                                    onClick={() => setLang(l)}
                                    className={`px-2 py-1 text-[10px] font-mono uppercase tracking-wider rounded-md transition-colors ${
                                        lang === l ? "bg-red-500 text-zinc-950" : "text-zinc-500 hover:text-zinc-300"
                                    }`}
                                    aria-pressed={lang === l}
                                >
                                    {l}
                                </button>
                            ))}
                        </div>
                        {walletConnected ? (
                            <ProfileMenu
                                walletAddress={walletAddress}
                                onDisconnect={disconnectWallet}
                            />
                        ) : (
                            <WalletConnect
                                connectWallet={t.connectWallet}
                                onConnected={handleConnectAndRedirect}
                            />
                        )}
                    </div>
                </div>
            </nav>

            {/* HERO */}
            <section className="relative mx-auto max-w-5xl px-6 pt-28 pb-20 text-center">
                <div className="inline-flex items-center gap-2 rounded-full border border-red-500/30 px-4 py-1 font-mono text-xs tracking-widest text-red-400 neon-text-red">
                    {t.badge}
                </div>

                <h1 className="mt-8 text-6xl md:text-7xl font-bold tracking-tighter leading-none neon-text-red">
                    {t.heroLine1}<br />
                    {t.heroLine2}
                </h1>

                <p className="mx-auto mt-6 max-w-2xl text-xl text-zinc-400">
                    {t.heroSub}
                </p>

                <div className="mt-12">
                    <LoopTicker labels={[t.observe, t.decide, t.execute, t.log]} />
                </div>

                <div className="mt-12 flex flex-wrap justify-center gap-4">
                    <Link to="/dashboard" className="neon-button group flex items-center gap-3 rounded-2xl bg-red-500 px-10 py-4 text-lg font-bold text-black hover:bg-red-600">
                        {t.ctaDashboard} <ArrowUpRight className="group-hover:rotate-45 transition" />
                    </Link>
                    <a href="https://testnet.cspr.live/contract-package/a44b0f0f83462cdc10172a0576ec760363fc1f25ca6dd92da9df1e2200a78c88" target="_blank" className="neon-border-button flex items-center gap-3 rounded-2xl border border-red-500/50 px-8 py-4 text-lg hover:border-red-400">
                        {t.ctaExplorer}
                    </a>
                </div>
            </section>

            {/* STATS */}
            <section className="mx-auto max-w-7xl px-6 py-12">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <div className="neon-box p-6">
                        <div className="text-4xl font-mono font-bold text-red-400">
                            {status?.actions_taken != null ? status.actions_taken.toLocaleString() : "—"}
                        </div>
                        <div className="text-sm text-zinc-500 mt-1">{t.stats.decisions}</div>
                    </div>
                    <div className="neon-box p-6">
                        <div className="text-4xl font-mono font-bold text-red-400">
                            {status?.status === "running" ? "LIVE" : status?.status ?? "—"}
                        </div>
                        <div className="text-sm text-zinc-500 mt-1">{t.stats.uptime}</div>
                    </div>
                    <div className="neon-box p-6">
                        <div className="text-4xl font-mono font-bold text-red-400">
                            {status?.last_market_data?.pool_apy != null
                                ? `+${(status.last_market_data.pool_apy - config.min_apy_delta).toFixed(1)}%`
                                : "—"}
                        </div>
                        <div className="text-sm text-zinc-500 mt-1">{t.stats.avgApy}</div>
                    </div>
                    <div className="neon-box p-6">
                        <div className="text-4xl font-mono font-bold text-red-400">
                            {Math.floor(config.check_interval_seconds / 60)}m
                        </div>
                        <div className="text-sm text-zinc-500 mt-1">{t.stats.latency}</div>
                    </div>
                </div>
            </section>

            {/* HOW IT WORKS */}
            <section id="how" className="mx-auto max-w-7xl px-6 py-20">
                <div className="text-center mb-12">
                    <h2 className="text-4xl font-bold neon-text-red">{t.howSub}</h2>
                    <p className="text-zinc-400 mt-3">
                        {lang === "en"
                            ? `Every ${Math.floor(config.check_interval_seconds / 60)} minutes the agent runs this cycle without human intervention.`
                            : `Cada ${Math.floor(config.check_interval_seconds / 60)} minutos el agente ejecuta este ciclo sin intervención humana.`}
                    </p>
                </div>

                <div className="grid gap-6 md:grid-cols-4">
                    {t.steps.map((step, i) => {
                        // Replace hardcoded thresholds in the Decide step (index 1)
                        const desc = i === 1
                            ? (lang === "en"
                                ? `Claude analyzes the conditions: if APY rises +${config.min_apy_delta}% and slippage < ${config.max_slippage_pct}%, the verdict is SWAP. Otherwise HOLD.`
                                : `Claude analiza las condiciones: si el APY sube +${config.min_apy_delta}% y slippage < ${config.max_slippage_pct}%, el veredicto es SWAP. Si no, HOLD.`)
                            : step.d;
                        return (
                            <div key={i} className="neon-box p-8 rounded-2xl border border-red-500/20 group">
                                <div className="text-red-500 text-5xl font-mono mb-4 opacity-30 group-hover:opacity-100 transition">0{i + 1}</div>
                                <h3 className="text-2xl font-bold mb-3">{step.t}</h3>
                                <p className="text-zinc-400 leading-relaxed">{desc}</p>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* FEATURES */}
            <section id="features" className="mx-auto max-w-7xl px-6 py-20 bg-black/40">
                <div className="text-center mb-12">
                    <h2 className="text-4xl font-bold neon-text-red">{t.featuresTitle}</h2>
                    <p className="text-zinc-400 mt-3">{t.featuresSub}</p>
                </div>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {t.features.map((f, i) => (
                        <div key={i} className="neon-box p-8 rounded-2xl border border-red-500/20">
                            <h3 className="text-xl font-semibold mb-3">{f.t}</h3>
                            <p className="text-zinc-400">{f.d}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ROADMAP */}
            <section id="roadmap" className="mx-auto max-w-7xl px-6 py-20">
                <div className="text-center mb-12">
                    <h2 className="text-4xl font-bold neon-text-red">{t.roadmapTitle}</h2>
                    <p className="text-zinc-400 mt-3">{t.roadmapSub}</p>
                </div>
                <div className="grid gap-6 md:grid-cols-3">
                    {t.roadmap.map((phase, i) => (
                        <div key={i} className="neon-box p-8 rounded-2xl border border-red-500/20">
                            <div className="uppercase text-red-400 text-sm tracking-widest mb-2">{phase.q}</div>
                            <div className="text-xl font-bold mb-6">{phase.label}</div>
                            <ul className="space-y-3">
                                {phase.items.map((item, j) => (
                                    <li key={j} className="flex gap-2 text-zinc-300">
                                        <span className="text-red-500 mt-1">→</span> {item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </section>

            {/* CTA */}
            <section className="mx-auto max-w-4xl px-6 py-24 text-center">
                <h2 className="text-5xl font-bold neon-text-red mb-4">{t.ctaTitle}</h2>
                <p className="text-xl text-zinc-400 mb-10">{t.ctaDesc}</p>
                <div className="flex flex-wrap justify-center gap-4">
                    <Link to="/dashboard" className="neon-button px-10 py-4 text-xl font-bold rounded-2xl">
                        {t.ctaDashboard}
                    </Link>
                    <a 
                        href="https://github.com/EstebanNahuelok/casper-yield-agent" 
                        target="_blank" 
                        className="neon-border-button px-10 py-4 text-xl rounded-2xl flex items-center gap-3"
                    >
                        {t.ctaSource} <Github />
                    </a>
                </div>
            </section>

            <footer className="border-t border-red-500/20 py-8 text-center text-sm text-zinc-500">
                {t.footer} • Built with neon and real on-chain decisions
            </footer>

            {/* Neon Styles */}
            <style jsx>{`
                .neon-text-red {
                    text-shadow: 0 0 15px #ff2d2d, 0 0 30px #ff2d2d, 0 0 60px #ff2d2d;
                }
                .neon-glow {
                    box-shadow: 0 0 25px #ff2d2d, 0 0 50px #ff2d2d;
                }
                .neon-button {
                    box-shadow: 0 0 25px #ff2d2d, 0 0 50px rgba(255,45,45,0.6);
                    transition: all 0.3s ease;
                }
                .neon-button:hover {
                    box-shadow: 0 0 40px #ff2d2d, 0 0 70px rgba(255,45,45,0.9);
                    transform: scale(1.03);
                }
                .neon-border-button {
                    border-color: #ff2d2d;
                    transition: all 0.3s ease;
                }
                .neon-border-button:hover {
                    box-shadow: 0 0 30px rgba(255,45,45,0.5);
                }
                .neon-box {
                    box-shadow: 0 0 20px rgba(255,45,45,0.25);
                    transition: all 0.3s ease;
                }
                .neon-box:hover {
                    box-shadow: 0 0 35px rgba(255,45,45,0.4);
                }
                .neon-step {
                    border-color: #3f3f46;
                }
                .neon-active {
                    border-color: #ff2d2d;
                    box-shadow: 0 0 30px #ff2d2d;
                    color: white;
                }
            `}</style>
        </div>
    );
};
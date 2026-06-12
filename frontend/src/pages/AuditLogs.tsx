
import { useMemo, useState } from "react";
import { ArrowLeft, Download, ExternalLink, Search, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { useAgentStatus } from "#hooks/useAgentStatus";

const EXPLORER = "https://testnet.cspr.live/deploy/";

type Lang = "en" | "es";

const dict = {
  en: {
    title: "Audit Logs",
    sub: "Immutable trail of every agent action on Casper Testnet.",
    back: "Back to dashboard",
    search: "Search by tx hash, pool, or action…",
    export: "Export CSV",
    time: "Timestamp",
    action: "Action",
    target: "Target",
    amount: "Amount",
    status: "Status",
    tx: "Tx",
    all: "All",
    success: "Success",
    pending: "Pending",
    observation: "Observation",
    failed: "Failed",
    totalEvents: "Total events",
    last24h: "Last 24h",
    successRate: "Success rate",
    avgGas: "Avg gas",
  },
  es: {
    title: "Logs de Auditoría",
    sub: "Traza inmutable de cada acción del agente en Casper Testnet.",
    back: "Volver al dashboard",
    search: "Buscar por hash, pool o acción…",
    export: "Exportar CSV",
    time: "Timestamp",
    action: "Acción",
    target: "Objetivo",
    amount: "Monto",
    status: "Estado",
    tx: "Tx",
    all: "Todos",
    success: "Éxito",
    pending: "Pendiente",
    observation: "Observación",
    failed: "Fallido",
    totalEvents: "Eventos totales",
    last24h: "Últimas 24h",
    successRate: "Tasa de éxito",
    avgGas: "Gas promedio",
  },
} as const;

export const AuditPage = () => {
  const { status } = useAgentStatus();
  const [lang, setLang] = useState<Lang>("en");
  const [filter, setFilter] = useState<"all" | "Success" | "Pending" | "Observation" | "Failed">("all");
  const [q, setQ] = useState("");
  const t = dict[lang];

  const entries = useMemo(() => {
    if (!status?.decision_history || status.decision_history.length === 0) return [];
    return status.decision_history.map((d: any, index: number) => ({
      id: `dh${index}`,
      ts: new Date(d.timestamp).toLocaleString(),
      action: d.action || "HOLD",
      target: "CSPR / sCSPR",
      amount: "—",
      status: d.deploy_hash ? "Success" : "Observation",
      hash: d.deploy_hash || "—",
      gas: "—",
    }));
  }, [status]);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (filter !== "all" && e.status !== filter) return false;
      if (!q.trim()) return true;
      const needle = q.toLowerCase();
      return e.hash.toLowerCase().includes(needle) ||
        e.action.toLowerCase().includes(needle) ||
        e.target.toLowerCase().includes(needle);
    });
  }, [entries, filter, q]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-sans pb-16 overflow-hidden">

      {/* Navbar con neon */}
      <nav className="border-b border-red-500/30 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="size-6 bg-red-500 rounded flex items-center justify-center neon-glow">
              <div className="size-2 bg-black rounded-full" />
            </div>
            <span className="font-medium text-zinc-100 tracking-tight neon-text-red">CASPER AUTOPILOT</span>
          </div>
          <Link to="/dashboard" className="flex items-center gap-2 text-red-400 hover:text-red-300 transition-colors">
            <ArrowLeft className="size-4" /> BACK
          </Link>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-6 py-10">
        <header className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-ping" />
            <span className="uppercase tracking-[3px] text-xs font-mono text-red-400 neon-text">LIVE AUDIT TRAIL</span>
          </div>
          <h1 className="text-5xl font-bold tracking-tighter neon-text-red">
            AUDIT LOGS
          </h1>
          <p className="text-zinc-400 mt-2">Inmutable record of agent decisions on Casper Testnet</p>
        </header>

        {/* Stats Neon */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: "TOTAL EVENTS", value: entries.length },
            { label: "LAST 24H", value: entries.length },
            { label: "SUCCESS RATE", value: "100%" },
            { label: "AVG GAS", value: "—" },
          ].map((s, i) => (
            <div key={i} className="neon-box p-6 border border-red-500/30 bg-zinc-900/50">
              <div className="text-[10px] tracking-widest text-red-400/70 mb-2">{s.label}</div>
              <div className="text-4xl font-mono text-red-400 neon-text">{s.value}</div>
            </div>
          ))}
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-4 text-red-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="SEARCH HASH / ACTION..."
            className="w-full bg-zinc-900 border border-red-500/40 focus:border-red-500 pl-12 py-4 rounded-2xl text-lg placeholder:text-zinc-600 focus:outline-none neon-input"
          />
        </div>

        {/* Table */}
        <div className="neon-table overflow-hidden rounded-3xl border border-red-500/20 bg-black/40">
          <table className="w-full">
            <thead>
              <tr className="border-b border-red-500/30 bg-zinc-950">
                <th className="px-8 py-5 text-left text-xs font-mono uppercase tracking-widest text-red-400">Timestamp</th>
                <th className="px-8 py-5 text-left text-xs font-mono uppercase tracking-widest text-red-400">Action</th>
                <th className="px-8 py-5 text-left text-xs font-mono uppercase tracking-widest text-red-400">Target</th>
                <th className="px-8 py-5 text-left text-xs font-mono uppercase tracking-widest text-red-400">Status</th>
                <th className="px-8 py-5 text-right text-xs font-mono uppercase tracking-widest text-red-400">TX HASH</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-red-500/10">
              {filtered.map((e, i) => (
                <tr key={i} className="hover:bg-red-500/5 group transition-all duration-200">
                  <td className="px-8 py-5 font-mono text-xs text-zinc-500">{e.ts}</td>
                  <td className="px-8 py-5">
                    <span className="font-mono font-bold text-red-400 group-hover:text-red-300 transition-colors">
                      {e.action}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-zinc-300">{e.target}</td>
                  <td className="px-8 py-5">
                    <span className={`px-4 py-1 text-xs font-mono rounded-full border ${e.status === "Success" ? "border-emerald-500 text-emerald-400 neon-success" : "border-zinc-700 text-zinc-400"}`}>
                      {e.status}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-right font-mono">
                    {e.hash !== "—" ? (
                      <a href={`${EXPLORER}${e.hash}`} target="_blank" rel="noreferrer"
                        className="text-red-400 hover:text-white inline-flex items-center gap-2 group-hover:neon-text">
                        {e.hash.slice(0, 10)}…
                        <ExternalLink className="size-4" />
                      </a>
                    ) : (
                      <span className="text-zinc-700">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

      {/* CSS Neon Animations */}
      <style jsx>{`
        .neon-text {
          text-shadow: 0 0 10px #ff2d2d,
                       0 0 20px #ff2d2d,
                       0 0 40px #ff2d2d;
        }
        .neon-text-red {
          text-shadow: 0 0 15px #ff2d2d,
                       0 0 30px #ff2d2d,
                       0 0 60px #ff2d2d;
        }
        .neon-glow {
          box-shadow: 0 0 15px #ff2d2d,
                      0 0 30px #ff2d2d;
        }
        .neon-box {
          box-shadow: 0 0 20px rgba(255, 45, 45, 0.3),
                      inset 0 0 15px rgba(255, 45, 45, 0.1);
        }
        .neon-input:focus {
          box-shadow: 0 0 0 4px rgba(255, 45, 45, 0.3);
        }
        .neon-table {
          box-shadow: 0 0 40px rgba(255, 45, 45, 0.15);
        }
        .neon-success {
          animation: neonPulse 2s infinite alternate;
        }
        @keyframes neonPulse {
          from { text-shadow: 0 0 5px #10b981; }
          to { text-shadow: 0 0 20px #10b981, 0 0 30px #10b981; }
        }
      `}</style>
    </div>
  );
};
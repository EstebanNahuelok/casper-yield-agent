import { useEffect, useState } from "react";
import { ArrowLeft, Check, Cpu, Shield, TrendingUp, Zap, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { useAgentConfig } from "#hooks/useAgentConfig";

type Lang = "en" | "es";
const dict = {
  en: {
    title: "Agent Strategy",
    sub: "Configure the autonomous decision policy. Changes propagate at the next epoch.",
    back: "Back to dashboard",
    riskProfile: "Risk profile",
    conservative: "Conservative",
    balanced: "Balanced",
    aggressive: "Aggressive",
    parameters: "Parameters",
    apyThreshold: "Minimum APY threshold",
    apyDesc: "Pools below this APY will be ignored by the scanner.",
    slippage: "Max slippage tolerance",
    slippageDesc: "Cancel a swap if observed slippage exceeds this value.",
    maxAlloc: "Max allocation per pool",
    maxAllocDesc: "Cap on the share of the vault deployed into a single pool.",
    minLiquidity: "Minimum pool liquidity",
    minLiquidityDesc: "Discard pools with TVL below this floor.",
    cycle: "Decision cycle",
    cycleDesc: "Frequency at which the agent re-evaluates positions.",
    behaviors: "Behaviors",
    autoCompound: "Auto-compound rewards",
    autoCompoundDesc: "Reinvest accumulated rewards every 6 hours.",
    autoExit: "Auto-exit on volatility spike",
    autoExitDesc: "Unwind positions if 5m volatility exceeds 8%.",
    blacklistMode: "Strict blacklist mode",
    blacklistModeDesc: "Block any pool flagged by the risk oracle.",
    save: "Save strategy",
    saved: "Saved (Preview)",
    reset: "Reset to defaults",
    summary: "Effective policy",
    summaryDesc: "What the agent will do at the next cycle.",
    previewBanner: "PREVIEW MODE — Strategy changes will be available in the next version.",
    comingSoon: "Coming soon",
    line1: "Scan 1 pool (CSPR/sCSPR) every 900s. Deploy capital where APY > {apy}%.",
    line2: "Limit each entry to {alloc}% of the vault with ≤ {slip}% slippage.",
    line3: "Auto-compound: {ac}. Auto-exit on spike: {ae}.",
    on: "on",
    off: "off",
  },
  es: {
    title: "Estrategia del agente",
    sub: "Configurá la política de decisión autónoma. Los cambios se aplican en el próximo epoch.",
    back: "Volver al dashboard",
    riskProfile: "Perfil de riesgo",
    conservative: "Conservador",
    balanced: "Balanceado",
    aggressive: "Agresivo",
    parameters: "Parámetros",
    apyThreshold: "Umbral mínimo de APY",
    apyDesc: "Los pools por debajo de este APY serán ignorados.",
    slippage: "Slippage máximo tolerado",
    slippageDesc: "Cancela un swap si el slippage observado supera este valor.",
    maxAlloc: "Asignación máxima por pool",
    maxAllocDesc: "Tope sobre la porción del vault desplegada en un solo pool.",
    minLiquidity: "Liquidez mínima del pool",
    minLiquidityDesc: "Descarta pools con TVL por debajo de este piso.",
    cycle: "Ciclo de decisión",
    cycleDesc: "Frecuencia con la que el agente re-evalúa posiciones.",
    behaviors: "Comportamientos",
    autoCompound: "Auto-compound de rewards",
    autoCompoundDesc: "Reinvierte rewards acumulados cada 6 horas.",
    autoExit: "Auto-salida ante volatilidad",
    autoExitDesc: "Cierra posiciones si la volatilidad a 5m supera 8%.",
    blacklistMode: "Modo blacklist estricto",
    blacklistModeDesc: "Bloquea cualquier pool marcado por el oráculo de riesgo.",
    save: "Guardar estrategia",
    saved: "Guardado (Vista previa)",
    reset: "Restablecer",
    summary: "Política efectiva",
    summaryDesc: "Lo que el agente hará en el próximo ciclo.",
    previewBanner: "MODO VISTA PREVIA — Los cambios de estrategia estarán disponibles en la próxima versión.",
    comingSoon: "Próximamente",
    line1: "Escanea 1 pool (CSPR/sCSPR) cada 900s. Despliega capital donde APY > {apy}%.",
    line2: "Limita cada entrada al {alloc}% del vault con slippage ≤ {slip}%.",
    line3: "Auto-compound: {ac}. Auto-salida ante spike: {ae}.",
    on: "on",
    off: "off",
  },
} as const;

type Profile = "conservative" | "balanced" | "aggressive";

const presets: Record<Profile, { apy: number; slip: number; alloc: number; liq: number; cycle: number }> = {
  conservative: { apy: 15, slip: 0.3, alloc: 20, liq: 2_000_000, cycle: 900 },
  balanced: { apy: 12.5, slip: 0.5, alloc: 35, liq: 1_000_000, cycle: 900 },
  aggressive: { apy: 8, slip: 1.2, alloc: 60, liq: 500_000, cycle: 900 },
};

export const StrategyPage = () => {
  const [lang, setLang] = useState<Lang>("en");
  const t = dict[lang];
  const agentConfig = useAgentConfig();

  const [profile, setProfile] = useState<Profile>("balanced");
  const [apy, setApy] = useState(presets.balanced.apy);
  const [slip, setSlip] = useState(presets.balanced.slip);
  const [alloc, setAlloc] = useState(presets.balanced.alloc);
  const [liq, setLiq] = useState(presets.balanced.liq);
  const [cycle, setCycle] = useState(agentConfig.check_interval_seconds);
  const [autoCompound, setAutoCompound] = useState(true);
  const [autoExit, setAutoExit] = useState(false);
  const [blacklist, setBlacklist] = useState(false);
  const [saved, setSaved] = useState(false);

  // Sync sliders with real agent config on first load
  useEffect(() => {
    setApy(agentConfig.min_apy_delta);
    setSlip(agentConfig.max_slippage_pct);
    setCycle(agentConfig.check_interval_seconds);
  }, [agentConfig.min_apy_delta, agentConfig.max_slippage_pct, agentConfig.check_interval_seconds]);

  const applyProfile = (p: Profile) => {
    setProfile(p);
    setApy(presets[p].apy);
    setSlip(presets[p].slip);
    setAlloc(presets[p].alloc);
    setLiq(presets[p].liq);
    setCycle(agentConfig.check_interval_seconds);
  };

  const save = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2200);
  };

  const reset = () => {
    applyProfile("balanced");
    setApy(agentConfig.min_apy_delta);
    setSlip(agentConfig.max_slippage_pct);
    setCycle(agentConfig.check_interval_seconds);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-sans pb-16">
      <nav className="border-b border-red-500/30 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-red-400 hover:text-red-300 transition-colors">
              <ArrowLeft className="size-4" /> {t.back.toUpperCase()}
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <div className="inline-flex items-center rounded-lg border border-red-500/30 bg-zinc-900/40 p-0.5">
              {(["en", "es"] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`px-2 py-1 text-[10px] font-mono uppercase tracking-wider rounded-md transition-colors ${lang === l ? "bg-red-500 text-zinc-950" : "text-zinc-500 hover:text-zinc-300"
                    }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-6 py-10">
        {/* PREVIEW BANNER */}
        <div className="mb-8 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 flex items-start gap-3">
          <AlertTriangle className="size-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-amber-400 font-medium text-sm">{t.previewBanner}</p>
          </div>
        </div>

        <header className="mb-8">
          <h1 className="text-3xl font-medium text-zinc-100 tracking-tight">{t.title}</h1>
          <p className="mt-2 text-sm text-zinc-500 max-w-2xl">{t.sub}</p>
        </header>

        <section className="mb-10">
          <h2 className="text-xs uppercase tracking-widest text-zinc-500 mb-3">{t.riskProfile}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {(
              [
                { id: "conservative", icon: Shield, label: t.conservative, desc: "APY ≥ 15%, slip ≤ 0.3%" },
                { id: "balanced", icon: Cpu, label: t.balanced, desc: "APY ≥ 12.5%, slip ≤ 0.5%" },
                { id: "aggressive", icon: Zap, label: t.aggressive, desc: "APY ≥ 8%, slip ≤ 1.2%" },
              ] as const
            ).map(({ id, icon: Icon, label, desc }) => (
              <button
                key={id}
                onClick={() => applyProfile(id)}
                className={`text-left p-4 rounded-xl border transition-colors ${profile === id
                    ? "border-red-500/60 bg-red-500/5"
                    : "border-zinc-900 bg-zinc-900/30 hover:border-zinc-800"
                  }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`size-4 ${profile === id ? "text-red-400" : "text-zinc-500"}`} />
                  <span className={`text-sm font-medium ${profile === id ? "text-zinc-100" : "text-zinc-300"}`}>
                    {label}
                  </span>
                </div>
                <p className="mt-2 text-[11px] font-mono text-zinc-500">{desc}</p>
              </button>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <section className="lg:col-span-7 space-y-6">
            <h2 className="text-xs uppercase tracking-widest text-zinc-500">{t.parameters}</h2>

            <ParamSlider
              label={t.apyThreshold}
              desc={t.apyDesc}
              value={apy}
              min={1}
              max={30}
              step={0.5}
              unit="%"
              onChange={setApy}
            />
            <ParamSlider
              label={t.slippage}
              desc={t.slippageDesc}
              value={slip}
              min={0.05}
              max={3}
              step={0.05}
              unit="%"
              onChange={setSlip}
            />
            <ParamSlider
              label={t.maxAlloc}
              desc={t.maxAllocDesc}
              value={alloc}
              min={5}
              max={100}
              step={5}
              unit="%"
              onChange={setAlloc}
            />
            <ParamSlider
              label={t.minLiquidity}
              desc={t.minLiquidityDesc}
              value={liq}
              min={100_000}
              max={5_000_000}
              step={100_000}
              unit=" CSPR"
              format={(v) => (v / 1_000_000).toFixed(1) + "M"}
              onChange={setLiq}
            />
            <ParamSlider
              label={t.cycle}
              desc={t.cycleDesc}
              value={cycle}
              min={300}
              max={1800}
              step={300}
              unit="s"
              onChange={setCycle}
            />

            <h2 className="text-xs uppercase tracking-widest text-zinc-500 pt-4">{t.behaviors}</h2>

            <Toggle
              label={t.autoCompound}
              desc={t.autoCompoundDesc}
              value={autoCompound}
              onChange={setAutoCompound}
              comingSoon={false}
            />
            <Toggle
              label={t.autoExit}
              desc={t.autoExitDesc}
              value={autoExit}
              onChange={setAutoExit}
              comingSoon={true}
            />
            <Toggle
              label={t.blacklistMode}
              desc={t.blacklistModeDesc}
              value={blacklist}
              onChange={setBlacklist}
              comingSoon={true}
            />

            <div className="flex items-center gap-3 pt-4">
              <button
                onClick={save}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-red-500 text-zinc-950 text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                {saved ? <Check className="size-4" /> : null}
                {saved ? t.saved : t.save}
              </button>
              <button
                onClick={reset}
                className="px-6 py-3 rounded-lg border border-zinc-800 text-sm text-zinc-300 hover:bg-zinc-900/60 transition-colors"
              >
                {t.reset}
              </button>
            </div>
          </section>

          <aside className="lg:col-span-5">
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 sticky top-24">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="size-4 text-red-400" />
                <h3 className="text-xs uppercase tracking-widest text-red-400">{t.summary}</h3>
              </div>
              <p className="text-[11px] text-zinc-500 mb-5">{t.summaryDesc}</p>

              <div className="space-y-4 text-sm leading-relaxed text-zinc-300">
                <p>{t.line1.replace("{apy}", apy.toString()).replace("900s", `${cycle}s`)}</p>
                <p>
                  {t.line2.replace("{alloc}", alloc.toString()).replace("{slip}", slip.toString())}
                </p>
                <p>
                  {t.line3
                    .replace("{ac}", autoCompound ? t.on : t.off)
                    .replace("{ae}", autoExit ? t.on : t.off)}
                </p>
              </div>

              <div className="mt-6 pt-6 border-t border-red-500/10 grid grid-cols-2 gap-4 text-xs font-mono">
                <Stat label="APY ≥" value={apy + "%"} />
                <Stat label="Slip ≤" value={slip + "%"} />
                <Stat label="Alloc ≤" value={alloc + "%"} />
                <Stat label="Cycle" value={`${cycle}s`} />
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

function ParamSlider({
  label,
  desc,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  format,
}: {
  label: string;
  desc: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}) {
  const display = format ? format(value) : value.toString();
  return (
    <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-900/30">
      <div className="flex items-baseline justify-between mb-1">
        <label className="text-sm text-zinc-200">{label}</label>
        <span className="text-sm font-mono text-red-400 tabular-nums">
          {display}
          {unit}
        </span>
      </div>
      <p className="text-[11px] text-zinc-500 mb-3">{desc}</p>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-red-500"
      />
    </div>
  );
}

function Toggle({
  label,
  desc,
  value,
  onChange,
  comingSoon = false,
}: {
  label: string;
  desc: string;
  value: boolean;
  onChange: (v: boolean) => void;
  comingSoon?: boolean;
}) {
  return (
    <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-900/30 flex items-start justify-between gap-4 relative">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <div className="text-sm text-zinc-200">{label}</div>
          {comingSoon && (
            <span className="text-[10px] px-2 py-0.5 bg-zinc-800 text-amber-400 rounded font-mono">
              {dict.en.comingSoon}
            </span>
          )}
        </div>
        <p className="text-[11px] text-zinc-500 mt-0.5">{desc}</p>
      </div>
      <button
        role="switch"
        aria-checked={value}
        disabled={comingSoon}
        onClick={() => !comingSoon && onChange(!value)}
        className={`shrink-0 mt-1 relative w-10 h-5 rounded-full transition-colors ${comingSoon ? "bg-zinc-800 cursor-not-allowed" : value ? "bg-red-500" : "bg-zinc-800"
          }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 size-4 rounded-full bg-zinc-950 transition-transform ${value && !comingSoon ? "translate-x-5" : ""
            }`}
        />
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="text-zinc-100 tabular-nums">{value}</div>
    </div>
  );
}
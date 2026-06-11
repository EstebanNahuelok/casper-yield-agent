# Casper Yield Agent

Agente autónomo de yield farming sobre **Casper Testnet**. Cada ciclo el agente:

1. **Observa** — lee el balance bloqueado en el contrato `YieldVault` (vía Casper RPC) y el estado del pool **CSPR/sCSPR** en `api.cspr.trade` (APY estimado y slippage).
2. **Decide** — manda los datos de mercado a un LLM (Groq) que devuelve una acción `SWAP` o `HOLD` con su razonamiento.
3. **Ejecuta** — si la decisión es `SWAP`, arma y firma el deploy contra el contrato; siempre registra la acción on-chain para que sea auditable.
4. **Expone** — publica el estado completo en una API HTTP (`GET /status`) que consume el dashboard.

El loop corre de forma supervisada: si crashea por una excepción no manejada, se reinicia solo tras unos segundos mientras la API sigue arriba.

---

## Componentes

| Pieza | Qué es | Dónde corre |
|-------|--------|-------------|
| **Agente** (`main.py`) | Loop de decisión + API FastAPI | Local, `:8000` |
| **Casper MCP Server** | Servidor .NET que el agente usa para balance, precios y para firmar/enviar deploys | Local, `:3001` |
| **api.cspr.trade** | REST remoto para APY/slippage del pool sCSPR | Remoto |
| **Groq** | LLM que toma la decisión `SWAP`/`HOLD` | Remoto |

---

## 1. Configurar el `.env`

Creá un archivo `.env` dentro de `agent/` (al lado de `main.py`). Variables:

| Variable | Obligatoria | Default | De dónde sale |
|----------|:-----------:|---------|---------------|
| `GROQ_API_KEY` | ✅ | — | Consola de [Groq](https://console.groq.com) → API Keys |
| `GROQ_MODEL` | — | `llama-3.3-70b-versatile` | ID del modelo en Groq |
| `CSPR_CLOUD_API_KEY` | ✅ | — | Dashboard de [cspr.cloud](https://cspr.cloud) → API key (la usa el MCP y las llamadas RPC directas) |
| `CASPER_MCP_URL` | — | `http://localhost:3001/mcp` | URL del Casper MCP local (ver paso 3) |
| `CSPRTRADE_MCP_URL` | — | `https://mcp.cspr.trade/mcp` | Endpoint remoto de CSPR.trade |
| `VAULT_PUBLIC_KEY` | ✅ | — | Clave pública de la wallet del agente/owner |
| `VAULT_OWNER_SECRET_KEY` | ✅ | — | Clave secreta (PEM en una línea) de esa wallet — **firma los deploys, no la commitees** |
| `VAULT_CONTRACT_HASH` | — | hash del deploy actual | `hash-...` del contrato `YieldVault` desplegado |
| `SCSPR_CONTRACT_HASH` | ✅ | — | Package hash del token/par sCSPR usado para cotizar swaps |
| `CASPER_NETWORK` | — | `testnet` | `testnet` o `mainnet` |
| `CHECK_INTERVAL_SECONDS` | — | `300` | Segundos entre ciclos del agente |
| `MIN_APY_DELTA` | — | `2.0` | Delta de APY mínimo (%) para justificar un swap |
| `MAX_SLIPPAGE_PCT` | — | `1.5` | Slippage máximo tolerado (%) |
| `MIN_BALANCE_CSPR` | — | `100.0` | Balance mínimo (CSPR) para operar |
| `API_HOST` | — | `0.0.0.0` | Host de la API del agente |
| `API_PORT` | — | `8000` | Puerto de la API del agente |

> ⚠️ Las variables con default ya están en `src/config.py`. Si las ponés en `.env`, **el `.env` gana** — no dejes valores placeholder (`hash-abc123...`), porque sobrescriben silenciosamente al default correcto.

Ejemplo mínimo:

```dotenv
GROQ_API_KEY=gsk_...
CSPR_CLOUD_API_KEY=019e...
VAULT_PUBLIC_KEY=01c3acc1...
VAULT_OWNER_SECRET_KEY=MC4CAQAwBQYDK2VwBCIEIL...
SCSPR_CONTRACT_HASH=a4f6d5e6...
CASPER_NETWORK=testnet
```

---

## 2. Instalar dependencias (con el venv)

El virtualenv vive en la **raíz del repo** (`../venv`), compartido por todo el proyecto.

```powershell
# Desde la raíz del repo: c:\PROYECTOS\casper-yield-agent
python -m venv venv                      # solo la primera vez
.\venv\Scripts\Activate.ps1              # activar (PowerShell)
pip install -r agent\requirements.txt
```

Si ya existe el venv, alcanza con activarlo. Para correr sin activar, usá el Python del venv directamente:
`c:\PROYECTOS\casper-yield-agent\venv\Scripts\python.exe`.

---

## 3. Levantar el Casper MCP Server

El agente **no arranca su loop** hasta poder conectarse al Casper MCP local (reintenta cada 30s). Levantalo primero, en modo HTTP sobre el puerto 3001:

```powershell
CasperMcp.exe --transport http --network testnet --port 3001
```

Notas:
- Tiene que ser `--transport http` (no `sse`): el servidor espera **POST** a `/mcp`; un GET devuelve `405`.
- La API key de cspr.cloud no va por CLI en modo HTTP — el agente la manda en el header `X-CSPR-Cloud-Api-Key` de cada request (la toma de `CSPR_CLOUD_API_KEY`).

---

## 4. Correr el agente

Con el MCP arriba y el `.env` configurado:

```powershell
cd agent
py main.py
```

Esto levanta a la vez:
- el **loop del agente** (observar → decidir → ejecutar cada `CHECK_INTERVAL_SECONDS`), y
- la **API** en `http://localhost:8000`.

Endpoints:
- `GET /status` — estado completo: último market data, última decisión, historial de las últimas 10 decisiones, balance, tx hash, errores.
- `GET /health` — chequeo de vida.

Frená con `Ctrl+C` (shutdown limpio: cancela loop y API).

---

## Atajo: `start-all.bat`

En la **raíz del repo** hay un `start-all.bat` que levanta todo el stack de una en ventanas separadas:

1. El **Casper MCP Server** (`:3001`)
2. El **agente** (`py main.py`, usando el Python del venv)
3. Un túnel **ngrok** sobre `:8000` para exponer la API al dashboard

```powershell
.\start-all.bat
```

Útil para demos: con un solo comando queda el MCP, el agente y el túnel público corriendo.

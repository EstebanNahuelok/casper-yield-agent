# Frontend — Casper Yield Agent Dashboard

Dashboard React + TypeScript + Vite que muestra el estado del agente de yield farming en tiempo real (balance, última decisión, historial, APY del pool CSPR/sCSPR, logs de auditoría).

Consume la API del agente: hace polling de `GET /status` **cada 30 segundos** ([useAgentStatus.ts](src/hooks/useAgentStatus.ts)).

## Requisitos

- Node.js 18+ y npm
- El **agente corriendo** y accesible (expone la API en `:8000`). Ver [../agent/README.md](../agent/README.md).

## Configuración

El frontend necesita saber dónde está la API del agente. Esto se define en `VITE_AGENT_API_URL`:

```bash
cp .env.example .env
```

Editá `.env`:

```dotenv
# Local (agente en la misma compu)
VITE_AGENT_API_URL=http://localhost:8000

# O, si exponés el agente con ngrok (ver start-all.bat en la raíz):
# VITE_AGENT_API_URL=https://<tu-subdominio>.ngrok-free.dev
```

> Si usás ngrok, la URL pública **cambia cada vez que reiniciás ngrok** (en el plan free), así que hay que actualizar `VITE_AGENT_API_URL` y reiniciar `npm run dev`. Para desarrollo local conviene `http://localhost:8000`.
>
> El cliente ya manda el header `ngrok-skip-browser-warning` ([agentApi.ts](src/api/agentApi.ts)), así que el túnel ngrok funciona sin la pantalla de advertencia.

## Correr en desarrollo

```bash
npm install      # solo la primera vez
npm run dev
```

Vite levanta el dashboard (por defecto en `http://localhost:5173`). Abrilo en el navegador; vas a ver los datos del agente actualizándose cada 30s. Si el agente no está arriba, la consola muestra `AGENT ERROR` y la vista queda sin datos.

## Build de producción

```bash
npm run build    # genera dist/
npm run preview  # sirve el build localmente para probar
```

Hay un `vercel.json` con el rewrite SPA (`/(.*) → /index.html`) por si lo deployás en Vercel.

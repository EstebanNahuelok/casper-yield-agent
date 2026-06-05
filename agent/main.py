import asyncio
import logging
import signal

import structlog
import uvicorn

from src.agent_loop import agent_loop
from src.api.server import app
from src.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
logging.basicConfig(level=logging.INFO)

log = structlog.get_logger()

AGENT_RESTART_DELAY = 10  # segundos antes de reiniciar el loop si crashea


async def _supervised_agent_loop() -> None:
    """
    Envuelve agent_loop con un supervisor: si crashea por una excepción
    no manejada, espera AGENT_RESTART_DELAY segundos y reinicia.
    La API sigue corriendo durante ese tiempo.
    """
    while True:
        try:
            await agent_loop()
            # agent_loop salió limpiamente (CancelledError) → no reiniciar
            return
        except asyncio.CancelledError:
            return
        except Exception as exc:
            log.error("supervisor.agent_crashed", error=str(exc), exc_info=True)
            log.info("supervisor.restarting", delay=AGENT_RESTART_DELAY)
            await asyncio.sleep(AGENT_RESTART_DELAY)


async def main() -> None:
    api_config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",
    )
    server = uvicorn.Server(api_config)

    # Crear las dos tareas independientes
    api_task = asyncio.create_task(server.serve(), name="api")
    agent_task = asyncio.create_task(_supervised_agent_loop(), name="agent")

    log.info(
        "main.started",
        api=f"http://{settings.api_host}:{settings.api_port}",
    )

    # Manejar Ctrl+C / SIGTERM limpiamente
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: _shutdown(api_task, agent_task))
        except NotImplementedError:
            # Windows no soporta add_signal_handler — KeyboardInterrupt alcanza
            pass

    try:
        await asyncio.gather(api_task, agent_task)
    except asyncio.CancelledError:
        pass


def _shutdown(*tasks: asyncio.Task) -> None:
    log.info("main.shutting_down")
    for task in tasks:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())

"""Memoria (checkpointer) de los grafos: Postgres si hay DATABASE_URL, RAM si no."""

import logging
import os
from dataclasses import dataclass
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# La base puede ser compartida por todo el curso: pocas conexiones por proceso.
POOL_MIN = 1
POOL_MAX = 2
TIMEOUT_CONEXION = 10.0


@dataclass
class Memoria:
    checkpointer: BaseCheckpointSaver
    tipo: Literal["ram", "postgres"]
    pool: object | None = None

    def cerrar(self) -> None:
        if self.pool is not None:
            self.pool.close()
            self.pool = None


def memoria_ram(motivo: str) -> Memoria:
    logger.warning("Usando memoria en RAM: %s", motivo)
    return Memoria(checkpointer=MemorySaver(), tipo="ram")


def abrir_pool(database_url: str):
    """Abre un pool pequeño que comprueba cada conexión antes de entregarla."""
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(
        conninfo=database_url,
        min_size=POOL_MIN,
        max_size=POOL_MAX,
        open=False,
        check=ConnectionPool.check_connection,
        timeout=TIMEOUT_CONEXION,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        name="memoria",
    )
    try:
        pool.open(wait=True, timeout=TIMEOUT_CONEXION)
    except Exception:
        pool.close()
        raise
    return pool


def abrir_memoria() -> Memoria:
    """Devuelve la memoria a usar; nunca lanza excepción: si Postgres falla, usa RAM."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return memoria_ram("DATABASE_URL no está configurada.")

    pool = None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        pool = abrir_pool(database_url)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
    except Exception as exc:
        if pool is not None:
            pool.close()
        # El mensaje de psycopg puede incluir la URL con la contraseña.
        detalle = str(exc).replace(database_url, "[DATABASE_URL]")
        return memoria_ram(f"Postgres no respondió ({type(exc).__name__}: {detalle}).")

    logger.info("Usando memoria en Postgres.")
    return Memoria(checkpointer=checkpointer, tipo="postgres", pool=pool)

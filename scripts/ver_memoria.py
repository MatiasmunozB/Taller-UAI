"""Muestra la memoria guardada en Postgres.

Uso:
    python scripts/ver_memoria.py              # lista los hilos guardados
    python scripts/ver_memoria.py THREAD_ID    # imprime los mensajes de un hilo
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.memoria import abrir_pool  # noqa: E402

LISTAR_HILOS_SQL = """
SELECT thread_id,
       count(*) AS checkpoints,
       max(checkpoint ->> 'ts') AS ultimo
FROM checkpoints
WHERE checkpoint_ns = ''
GROUP BY thread_id
ORDER BY ultimo DESC
"""


def listar_hilos(pool) -> None:
    with pool.connection() as conn:
        filas = conn.execute(LISTAR_HILOS_SQL).fetchall()
    if not filas:
        print("No hay hilos guardados.")
        return
    ancho = max(len("thread_id"), *(len(f["thread_id"]) for f in filas))
    print(f"{'thread_id':<{ancho}}  checkpoints  último")
    for f in filas:
        ultimo = (f["ultimo"] or "")[:19].replace("T", " ")
        print(f"{f['thread_id']:<{ancho}}  {f['checkpoints']:>11}  {ultimo} UTC")


def mostrar_hilo(pool, thread_id: str) -> int:
    from langgraph.checkpoint.postgres import PostgresSaver

    tupla = PostgresSaver(pool).get_tuple({"configurable": {"thread_id": thread_id}})
    if tupla is None:
        print(f"No existe el hilo '{thread_id}'.")
        return 1
    mensajes = tupla.checkpoint["channel_values"].get("messages", [])
    if not mensajes:
        print(f"El hilo '{thread_id}' no tiene mensajes.")
        return 0
    etiquetas = {"human": "Usuario", "ai": "Agente", "system": "Sistema"}
    for i, mensaje in enumerate(mensajes, start=1):
        quien = etiquetas.get(mensaje.type, mensaje.type)
        print(f"{i}. {quien}: {mensaje.content}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Muestra la memoria guardada en Postgres.")
    parser.add_argument("thread_id", nargs="?", help="Hilo a mostrar; sin él, lista todos.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("Falta DATABASE_URL en .env: la memoria en RAM no se puede ver desde otro proceso.")
        return 1

    pool = abrir_pool(database_url)
    try:
        if args.thread_id:
            return mostrar_hilo(pool, args.thread_id)
        listar_hilos(pool)
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())

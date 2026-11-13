"""Punto de entrada CLI para ejecutar agentes desde la raíz del proyecto."""

import argparse
import logging
import os
from uuid import uuid4

from dotenv import load_dotenv

from src.memoria import abrir_memoria
from src.router.graph import build_graph


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Ejecuta un agente del proyecto.")
    parser.add_argument("agente", help="Nombre del agente (por ahora: router).")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente.")
    parser.add_argument("--saltos", action="store_true", help="Muestra los nodos recorridos.")
    parser.add_argument("--diagrama", action="store_true", help="Muestra el grafo Mermaid.")
    parser.add_argument(
        "--hilo",
        "--thread-id",
        dest="hilo",
        metavar="NOMBRE",
        help="thread_id de la conversación; usa el mismo para que recuerde lo anterior.",
    )
    args = parser.parse_args()

    if args.agente != "router":
        parser.error("El único agente disponible por ahora es 'router'.")

    if args.diagrama:
        # El diagrama no necesita memoria: no abre conexiones a la base.
        print(build_graph().get_graph().draw_mermaid())
        return
    if args.mensaje is None:
        parser.error("mensaje es obligatorio salvo que uses --diagrama.")

    memoria = abrir_memoria()
    try:
        graph = build_graph(checkpointer=memoria.checkpointer)
        hilo = args.hilo or os.getenv("THREAD_ID") or str(uuid4())
        config = {"configurable": {"thread_id": hilo}}

        if args.saltos:
            saltos = []
            for update in graph.stream({"mensaje": args.mensaje}, config, stream_mode="updates"):
                saltos.extend(name for name in update if not name.startswith("__"))
            state = graph.get_state(config).values
            print(f"Saltos: {' → '.join(saltos)}")
            print(f"Motivo: {state['motivo']}")
        else:
            state = graph.invoke({"mensaje": args.mensaje}, config)

        print(f"Memoria: {memoria.tipo} · hilo: {hilo}")
        print(f"Ruta: {state['ruta']}")
        print(f"Respuesta: {state['respuesta']}")
    finally:
        memoria.cerrar()


if __name__ == "__main__":
    main()

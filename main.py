"""Punto de entrada CLI para ejecutar agentes desde la raíz del proyecto."""

import argparse
import os
from uuid import uuid4

from dotenv import load_dotenv

from src.router.graph import build_graph


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ejecuta un agente del proyecto.")
    parser.add_argument("agente", help="Nombre del agente (por ahora: router).")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente.")
    parser.add_argument("--saltos", action="store_true", help="Muestra los nodos recorridos.")
    parser.add_argument("--diagrama", action="store_true", help="Muestra el grafo Mermaid.")
    parser.add_argument("--thread-id", help="ID para recuperar la memoria de una conversación.")
    args = parser.parse_args()

    if args.agente != "router":
        parser.error("El único agente disponible por ahora es 'router'.")

    graph = build_graph()
    if args.diagrama:
        print(graph.get_graph().draw_mermaid())
        return
    if args.mensaje is None:
        parser.error("mensaje es obligatorio salvo que uses --diagrama.")

    config = {
        "configurable": {
            "thread_id": args.thread_id or os.getenv("THREAD_ID") or str(uuid4())
        }
    }
    if args.saltos:
        saltos = []
        for update in graph.stream({"mensaje": args.mensaje}, config, stream_mode="updates"):
            saltos.extend(name for name in update if not name.startswith("__"))
        state = graph.get_state(config).values
        print(f"Saltos: {' → '.join(saltos)}")
        print(f"Motivo: {state['motivo']}")
    else:
        state = graph.invoke({"mensaje": args.mensaje}, config)

    print(f"Ruta: {state['ruta']}")
    print(f"Respuesta: {state['respuesta']}")


if __name__ == "__main__":
    main()

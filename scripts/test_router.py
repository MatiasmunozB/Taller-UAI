"""Evalúa las rutas del agente router con los casos de tests/casos_router.json."""

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.router.graph import build_graph  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.getenv("GOOGLE_API_KEY"):
        print("Falta GOOGLE_API_KEY. Configúrala en .env antes de ejecutar la evaluación.")
        return 2

    cases_path = ROOT / "tests" / "casos_router.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    graph = build_graph()
    results = []

    for index, case in enumerate(cases, start=1):
        state = graph.invoke(
            {"mensaje": case["mensaje"]},
            {"configurable": {"thread_id": f"router-eval-{index}-{uuid4()}"}},
        )
        results.append(
            {
                **case,
                "obtenido": state["ruta"],
                "motivo": state["motivo"],
                "ok": state["ruta"] == case["esperado"],
            }
        )

    columns = ["Mensaje", "Esperado", "Obtenido", "OK", "Motivo"]
    rows = [
        [r["mensaje"], r["esperado"], r["obtenido"], "✔" if r["ok"] else "✘", r["motivo"]]
        for r in results
    ]
    widths = [max(len(columns[i]), *(len(row[i]) for row in rows)) for i in range(len(columns))]
    print(" | ".join(name.ljust(widths[i]) for i, name in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))

    hits = sum(result["ok"] for result in results)
    total = len(results)
    print(f"\nAciertos: {hits}/{total} ({hits / total:.1%})")
    failed = [result for result in results if not result["ok"]]
    if failed:
        print("Fallados:")
        for result in failed:
            print(f"- {result['mensaje']} (esperado: {result['esperado']}, obtenido: {result['obtenido']})")
    else:
        print("Fallados: ninguno")
    return 0 if hits >= 13 else 1


if __name__ == "__main__":
    raise SystemExit(main())

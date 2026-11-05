"""Pruebas de integración del router; requieren GOOGLE_API_KEY para llamar a Gemini."""

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from src.router.graph import build_graph

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
CASES = json.loads(Path(__file__).with_name("casos_router.json").read_text(encoding="utf-8"))
RESULTS = []


@pytest.fixture(scope="module")
def router_graph():
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("Configura GOOGLE_API_KEY en .env para ejecutar las pruebas de integración.")

    graph = build_graph()
    yield graph

    hits = sum(RESULTS)
    assert len(RESULTS) == len(CASES), f"Se evaluaron {len(RESULTS)} de {len(CASES)} casos."
    assert hits >= 13, f"El router acertó {hits}/{len(CASES)}; se requieren al menos 13/15."


@pytest.mark.parametrize("case", CASES, ids=[case["mensaje"] for case in CASES])
def test_router_case(case, router_graph):
    state = router_graph.invoke(
        {"mensaje": case["mensaje"]},
        {"configurable": {"thread_id": f"pytest-router-{uuid4()}"}},
    )

    assert state["ruta"] in {"preventa", "postventa", "generica"}
    assert state["motivo"].strip()
    assert state["respuesta"].strip()
    RESULTS.append(state["ruta"] == case["esperado"])

"""Pruebas de la API: /chat exige X-API-Key. No llaman al modelo real."""

import pytest
from fastapi.testclient import TestClient

from api.app import app

CLAVE_PRUEBA = "clave-de-prueba"
BODY = {"user_id": "cliente-test", "texto": "¿tienen la polera azul en talla M?"}


class GrafoFalso:
    """Reemplaza al grafo para no gastar cuota del modelo."""

    def invoke(self, entrada, config):
        return {
            "ruta": "preventa",
            "motivo": "Pregunta por un producto.",
            "respuesta": f"Recibí: {entrada['mensaje']}",
        }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", CLAVE_PRUEBA)
    with TestClient(app) as test_client:
        app.state.router_graph = GrafoFalso()
        yield test_client


def test_chat_sin_clave_responde_401(client):
    response = client.post("/chat", json=BODY)
    assert response.status_code == 401
    assert "X-API-Key" in response.json()["detail"]


def test_chat_con_clave_responde_200(client):
    response = client.post("/chat", json=BODY, headers={"X-API-Key": CLAVE_PRUEBA})
    assert response.status_code == 200
    assert set(response.json()) == {"ruta", "motivo", "respuesta"}

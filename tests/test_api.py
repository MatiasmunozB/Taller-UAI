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
    # Sin base de datos: las pruebas no deben tocar el Postgres compartido.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as test_client:
        app.state.router_graph = GrafoFalso()
        yield test_client


def test_health_informa_memoria_ram_sin_base(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["memoria"] == "ram"


def test_postgres_caido_usa_ram(monkeypatch):
    from src import memoria

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/nada")
    monkeypatch.setattr(memoria, "TIMEOUT_CONEXION", 1.0)
    resultado = memoria.abrir_memoria()
    assert resultado.tipo == "ram"
    assert resultado.pool is None


def test_chat_sin_clave_responde_401(client):
    response = client.post("/chat", json=BODY)
    assert response.status_code == 401
    assert "X-API-Key" in response.json()["detail"]


def test_chat_con_clave_responde_200(client):
    response = client.post("/chat", json=BODY, headers={"X-API-Key": CLAVE_PRUEBA})
    assert response.status_code == 200
    assert set(response.json()) == {"ruta", "motivo", "respuesta"}

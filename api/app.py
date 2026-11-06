"""API HTTP para el agente router de ecommerce."""

import hmac
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from src.router.graph import build_graph

load_dotenv()
logger = logging.getLogger(__name__)
MODELO = os.getenv("MODELO", "gemini-3.5-flash-lite")


class HealthResponse(BaseModel):
    """Estado básico de la API y nombre del modelo configurado."""

    ok: bool = Field(description="Indica si la API está disponible.", examples=[True])
    modelo: str = Field(
        description="Nombre del modelo configurado para clasificar mensajes.",
        examples=["gemini-3.5-flash-lite"],
    )


class ChatRequest(BaseModel):
    """Mensaje de un usuario para clasificar y enrutar."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"user_id": "cliente-123", "texto": "¿tienen la polera azul en talla M?"}
            ]
        }
    )

    user_id: str = Field(
        description="Identificador estable del usuario; se utiliza como thread_id de memoria.",
        examples=["cliente-123"],
    )
    texto: str = Field(
        description="Mensaje del usuario que recibirá el agente router.",
        examples=["¿tienen la polera azul en talla M?"],
    )


class ChatResponse(BaseModel):
    """Clasificación del mensaje y respuesta del agente de destino."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ruta": "preventa",
                    "motivo": "El cliente pregunta por la disponibilidad de un producto antes de comprar.",
                    "respuesta": "Soy el agente de preventa. Recibí: ¿tienen la polera azul en talla M?. Pronto podré ayudarte con productos y compras.",
                }
            ]
        }
    )

    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="Ruta seleccionada por el router.",
        examples=["preventa"],
    )
    motivo: str = Field(
        description="Motivo breve por el que se eligió la ruta.",
        examples=["El cliente pregunta por un producto antes de comprar."],
    )
    respuesta: str = Field(
        description="Respuesta generada por el nodo de destino.",
        examples=["Soy el agente de preventa. Recibí: hola. Pronto podré ayudarte con productos y compras."],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Compila el grafo una sola vez para toda la vida de la aplicación."""
    app.state.router_graph = build_graph()
    yield


app = FastAPI(
    title="Ecommerce Router API",
    version="1.0.0",
    description=(
        "Clasifica mensajes de clientes de ecommerce y los enruta a preventa, "
        "postventa o respuestas genéricas. La conversación se conserva por user_id."
    ),
    openapi_tags=[
        {"name": "salud", "description": "Estado y configuración de la API."},
        {"name": "chat", "description": "Clasificación y respuesta a mensajes de clientes."},
        {"name": "telegram", "description": "Webhook seguro para actualizaciones de Telegram."},
    ],
    lifespan=lifespan,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["salud"],
    summary="Comprobar el estado de la API",
    description="Devuelve el estado del servicio y el nombre del modelo configurado.",
)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, modelo=MODELO)


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Enrutar un mensaje de ecommerce",
    description=(
        "Clasifica el mensaje como preventa, postventa o genérica y devuelve "
        "el motivo y la respuesta del agente correspondiente."
    ),
    responses={
        200: {"description": "El mensaje se clasificó y respondió correctamente."},
        422: {
            "description": "El body no cumple el esquema requerido; por ejemplo, falta texto.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "missing",
                                "loc": ["body", "texto"],
                                "msg": "Field required",
                                "input": {"user_id": "cliente-123"},
                            }
                        ]
                    }
                }
            },
        },
        502: {
            "description": "El modelo o el grafo no pudo procesar el mensaje.",
            "content": {
                "application/json": {
                    "example": {"detail": "No se pudo procesar el mensaje en este momento."}
                }
            },
        },
    },
)
async def chat(
    request: Request,
    payload: ChatRequest = Body(
        ...,
        openapi_examples={
            "preventa": {
                "summary": "Consulta de preventa",
                "value": {
                    "user_id": "cliente-123",
                    "texto": "¿tienen la polera azul en talla M?",
                },
            }
        },
    ),
) -> ChatResponse:
    try:
        result = await run_in_threadpool(
            request.app.state.router_graph.invoke,
            {"mensaje": payload.texto},
            {"configurable": {"thread_id": payload.user_id}},
        )
    except Exception as exc:
        logger.exception("Falló la ejecución del grafo router")
        raise HTTPException(
            status_code=502,
            detail="No se pudo procesar el mensaje en este momento.",
        ) from exc

    return ChatResponse(
        ruta=result["ruta"],
        motivo=result["motivo"],
        respuesta=result["respuesta"],
    )


@app.post(
    "/telegram",
    tags=["telegram"],
    include_in_schema=False,
)
async def telegram(
    request: Request,
    payload: Any = Body(...),
    telegram_secret: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, bool]:
    expected_secret = os.getenv("TELEGRAM_SECRET", "")
    if not expected_secret or not telegram_secret or not hmac.compare_digest(
        telegram_secret, expected_secret
    ):
        raise HTTPException(status_code=403, detail="Secreto de Telegram inválido.")

    if not isinstance(payload, dict):
        return {"ok": True}

    message = payload.get("message")
    if not isinstance(message, dict):
        return {"ok": True}

    chat = message.get("chat")
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    texto = message.get("text")
    if chat_id is None or not isinstance(texto, str) or not texto.strip():
        return {"ok": True}

    try:
        result = await run_in_threadpool(
            request.app.state.router_graph.invoke,
            {"mensaje": texto},
            {"configurable": {"thread_id": str(chat_id)}},
        )
        logger.info("Telegram chat_id=%s ruta=%s", chat_id, result["ruta"])

        bot_token = os.getenv("TELEGRAM_TOKEN", "")
        if not bot_token:
            raise RuntimeError("TELEGRAM_TOKEN no está configurado.")

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": result["respuesta"]},
            )
            response.raise_for_status()
            telegram_result = response.json()
            if not telegram_result.get("ok"):
                raise RuntimeError("Telegram sendMessage devolvió ok=false.")
    except Exception as exc:
        # Los mensajes de error HTTP pueden incluir el token en la URL: se redactan antes del log.
        details = str(exc)
        for secret_name in ("TELEGRAM_TOKEN", "TELEGRAM_SECRET", "GOOGLE_API_KEY"):
            secret = os.getenv(secret_name, "")
            if secret:
                details = details.replace(secret, "[REDACTED]")
        logger.error("Error procesando update de Telegram (%s): %s", type(exc).__name__, details)

    return {"ok": True}

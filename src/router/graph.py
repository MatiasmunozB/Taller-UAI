"""Grafo LangGraph para clasificar y enrutar mensajes de ecommerce."""

import logging
import os
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.router import prompts

logger = logging.getLogger(__name__)
TIENDA_PATH = Path(__file__).resolve().parents[2] / "data" / "tienda.md"


def cargar_tienda() -> str:
    """Lee data/tienda.md; si no existe, el asistente queda sin datos de la tienda."""
    try:
        return TIENDA_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("No se pudo leer %s; respuesta_generica no tendrá datos de la tienda.", TIENDA_PATH)
        return "(sin información de la tienda)"


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="A qué agente va el mensaje."
    )
    motivo: str = Field(description="Una frase: por qué esa ruta.")


class RouterState(TypedDict, total=False):
    mensaje: str
    ruta: Literal["preventa", "postventa", "generica"]
    motivo: str
    respuesta: str
    messages: Annotated[list[BaseMessage], add_messages]


def build_graph(llm=None, checkpointer=None):
    """Construye el grafo.

    ``llm`` opcional permite probarlo sin API externa. ``checkpointer`` es la
    memoria de las conversaciones; si no se entrega, se usa RAM (MemorySaver).
    """
    base_llm = llm
    structured_llm = None
    prompt_generica = prompts.PROMPT_RESPUESTA_GENERICA.format(tienda=cargar_tienda())

    def obtener_llm():
        """Crea el modelo la primera vez que se necesita (no al compilar el grafo)."""
        nonlocal base_llm
        if base_llm is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            base_llm = ChatGoogleGenerativeAI(
                model=os.getenv("MODELO", "gemini-3.5-flash-lite"),
                google_api_key=os.getenv("GOOGLE_API_KEY") or None,
            )
        return base_llm

    def router_node(state: RouterState) -> dict:
        nonlocal structured_llm
        if structured_llm is None:
            structured_llm = obtener_llm().with_structured_output(Decision)

        mensaje = state["mensaje"]
        current_message = HumanMessage(content=mensaje)
        decision = structured_llm.invoke(
            [
                SystemMessage(content=prompts.PROMPT_ROUTER),
                *state.get("messages", []),
                current_message,
            ]
        )
        return {
            "ruta": decision.ruta,
            "motivo": decision.motivo,
            "messages": [current_message],
        }

    def preventa_node(state: RouterState) -> dict:
        respuesta = prompts.PROMPT_AGENTE_PREVENTA.format(mensaje=state["mensaje"])
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    def postventa_node(state: RouterState) -> dict:
        respuesta = prompts.PROMPT_AGENTE_POSTVENTA.format(mensaje=state["mensaje"])
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    def generica_node(state: RouterState) -> dict:
        # El historial ya incluye el mensaje actual: lo agregó el router.
        try:
            salida = obtener_llm().invoke(
                [SystemMessage(content=prompt_generica), *state.get("messages", [])]
            )
            respuesta = salida.text.strip() or prompts.RESPUESTA_GENERICA
        except Exception:
            logger.exception("El modelo no respondió en respuesta_generica; uso la frase fija.")
            respuesta = prompts.RESPUESTA_GENERICA
        return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}

    builder = StateGraph(RouterState)
    builder.add_node("router", router_node)
    builder.add_node("agente_preventa", preventa_node)
    builder.add_node("agente_postventa", postventa_node)
    builder.add_node("respuesta_generica", generica_node)
    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        lambda state: state["ruta"],
        {
            "preventa": "agente_preventa",
            "postventa": "agente_postventa",
            "generica": "respuesta_generica",
        },
    )
    builder.add_edge("agente_preventa", END)
    builder.add_edge("agente_postventa", END)
    builder.add_edge("respuesta_generica", END)
    return builder.compile(checkpointer=checkpointer or MemorySaver())

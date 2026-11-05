"""Grafo LangGraph para clasificar y enrutar mensajes de ecommerce."""

import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.router import prompts


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


def build_graph(llm=None):
    """Construye el grafo; ``llm`` opcional permite probarlo sin API externa."""
    structured_llm = llm.with_structured_output(Decision) if llm is not None else None

    def router_node(state: RouterState) -> dict:
        nonlocal structured_llm
        if structured_llm is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            structured_llm = ChatGoogleGenerativeAI(
                model=os.getenv("MODELO", "gemini-3.5-flash-lite"),
                google_api_key=os.getenv("GOOGLE_API_KEY") or None,
            ).with_structured_output(Decision)

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
        return {
            "respuesta": prompts.RESPUESTA_GENERICA,
            "messages": [AIMessage(content=prompts.RESPUESTA_GENERICA)],
        }

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
    return builder.compile(checkpointer=MemorySaver())

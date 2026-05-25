"""Endpoint del chat lateral (PR-0 stub).

Persona B sustituye este stub en F3-04. Invariantes a respetar al
reemplazarlo (ver CLAUDE.md):

  - El chat NUNCA escribe en el estado del wizard.
  - Si el RAG no devuelve fragmentos relevantes, la respuesta canónica es
    "No tengo información suficiente para responder con base normativa"
    y `citation = None`.
  - Toda respuesta exitosa incluye `[Reglamento X, Art. Y]` y un objeto
    `Citation` poblado.
"""

from fastapi import APIRouter, Response

from app.api.v1.schemas import ChatFragment, ChatRequest, ChatResponse, Citation

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_stub(body: ChatRequest, response: Response) -> ChatResponse:
    """STUB de F3-04. Devuelve respuesta fija con cita normativa simulada."""
    response.headers["X-Stub"] = "true"
    return ChatResponse(
        answer=(
            "Para baterías industriales recargables, el Reglamento UE 2023/1542 "
            "exige declarar la huella de carbono, el contenido reciclado y la "
            "capacidad nominal, entre otros. [Reglamento UE 2023/1542, Art. 7]"
        ),
        citation=Citation(
            regulation="Reglamento UE 2023/1542",
            article="Art. 7",
            url=None,
        ),
        fragments=[
            ChatFragment(
                cita="Reglamento UE 2023/1542, Art. 7",
                texto=(
                    "Los productores facilitarán a los consumidores y a otros "
                    "usuarios finales información clara, fiable y pertinente sobre "
                    "las baterías…"
                ),
                score=0.82,
            ),
        ],
    )

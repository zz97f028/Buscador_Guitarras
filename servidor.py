from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "datos" / "anuncios.json"
MODEL = "gpt-6-luna"
NO_WEB_RESULTS = (
    "No he encontrado resultados web con fuentes verificables para esta consulta."
)

load_dotenv(ROOT / ".env")
with DATA_PATH.open(encoding="utf-8") as data_file:
    DOCUMENTS: list[dict[str, str | int | None]] = json.load(data_file)
CLIENT = OpenAI()


class Mensaje(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class PreguntaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pregunta: str = Field(min_length=1, max_length=1000)
    historial: list[Mensaje] = Field(default_factory=list, max_length=20)

    @field_validator("pregunta")
    @classmethod
    def pregunta_no_vacia(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La pregunta no puede estar vacía.")
        return value.strip()


class Fuente(BaseModel):
    id: str
    portal: str
    titulo: str
    url: str


class PreguntaResponse(BaseModel):
    respuesta: str
    fuentes: list[Fuente]


class Documento(BaseModel):
    id: str
    titulo: str
    marca: str
    modelo: str
    anio: int | None
    tipo: str
    precio: int
    estado: str
    ciudad: str
    portal: str
    fecha: str
    fragmento: str
    url: str | None
    ficticio: bool


class DocumentosResponse(BaseModel):
    total: int
    documentos: list[Documento]


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _web_sources(response: object) -> list[Fuente]:
    sources: list[Fuente] = []
    seen_urls: set[str] = set()
    for output_item in getattr(response, "output", []):
        if getattr(output_item, "type", None) != "message":
            continue
        for content in getattr(output_item, "content", []):
            if getattr(content, "type", None) != "output_text":
                continue
            for annotation in getattr(content, "annotations", []):
                if getattr(annotation, "type", None) != "url_citation":
                    continue
                url = str(getattr(annotation, "url", "")).strip()
                try:
                    parsed_url = urlsplit(url)
                except ValueError:
                    continue
                if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
                    continue
                if parsed_url.username or parsed_url.password:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title = str(getattr(annotation, "title", "") or parsed_url.hostname)
                sources.append(
                    Fuente(
                        id=f"WEB-{len(sources) + 1:02d}",
                        portal=parsed_url.hostname.removeprefix("www."),
                        titulo=title,
                        url=url,
                    )
                )
    return sources


def _answer(question: PreguntaRequest) -> PreguntaResponse:
    history = "\n".join(
        f"{message.role}: {message.content}" for message in question.historial
    )
    instructions = (
        "Responde en español sobre anuncios actuales de guitarras de segunda mano. "
        "Usa la búsqueda web obligatoria para buscar anuncios relevantes para la pregunta "
        "actual y basa los datos concretos únicamente en los resultados web consultados. "
        "Si no se especifica un país, busca anuncios situados en España y no presentes "
        "resultados de otros países como si fueran opciones locales. Prioriza anuncios "
        "individuales frente a páginas de categorías. Resume cada opción en una frase breve "
        "con precio, ubicación y estado solo cuando la página los publique. Distingue lo que "
        "afirma el vendedor de lo verificado de forma independiente; no declares que un anuncio "
        "sigue activo si la fuente no lo confirma. No inventes anuncios ni completes datos "
        "ausentes. Si no encuentras fuentes web relevantes para la ubicación solicitada, dilo "
        "claramente en vez de sustituirlas por resultados de otra región. Responde en texto "
        "sencillo, sin tablas, formato Markdown ni enlaces: las fuentes enlazadas aparecerán "
        "debajo de la respuesta. El historial solo aporta contexto para interpretar la pregunta "
        "actual y no es una fuente de hechos."
    )
    response = CLIENT.responses.create(
        model=MODEL,
        tools=[{"type": "web_search", "search_context_size": "medium"}],
        tool_choice="required",
        instructions=instructions,
        input=(
            "Busca en la web ahora. Consulta actual:\n"
            f"{question.pregunta}\n\n"
            f"Historial reciente (solo contexto):\n{history or '(sin historial)'}"
        ),
    )
    sources = _web_sources(response)
    if not sources:
        return PreguntaResponse(respuesta=NO_WEB_RESULTS, fuentes=[])
    answer = re.sub(
        r"\[([^\]]+)\]\(https?://[^)\s]+\)",
        r"\1",
        response.output_text,
    )
    answer = re.sub(r"cite[^]+", "", answer).strip()
    return PreguntaResponse(respuesta=answer, fuentes=sources)


app = FastAPI(title="Acorde · API de anuncios")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.post("/api/preguntar", response_model=PreguntaResponse)
def preguntar(request: PreguntaRequest) -> PreguntaResponse:
    return _answer(request)


@app.get("/api/documentos", response_model=DocumentosResponse)
def documentos(
    q: Annotated[str | None, Query(max_length=200)] = None,
    marca: Annotated[str | None, Query(max_length=80)] = None,
    tipo: Annotated[str | None, Query(max_length=80)] = None,
    portal: Annotated[str | None, Query(max_length=100)] = None,
) -> DocumentosResponse:
    filtered = DOCUMENTS
    if q and q.strip():
        query = _normalized(q)
        filtered = [
            document
            for document in filtered
            if query in _normalized(" ".join(str(value) for value in document.values()))
        ]
    if marca and marca.strip():
        brand = _normalized(marca)
        filtered = [
            document for document in filtered if _normalized(str(document["marca"])) == brand
        ]
    if tipo and tipo.strip():
        instrument_type = _normalized(tipo)
        filtered = [
            document
            for document in filtered
            if _normalized(str(document["tipo"])) == instrument_type
        ]
    if portal and portal.strip():
        source = _normalized(portal)
        filtered = [
            document
            for document in filtered
            if _normalized(str(document["portal"])) == source
        ]
    return DocumentosResponse(
        total=len(filtered),
        documentos=[Documento.model_validate(document) for document in filtered],
    )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ACORDE_API_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("ACORDE_API_PORT debe estar entre 1 y 65535.")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()

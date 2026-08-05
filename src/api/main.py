"""FastAPI application entrypoint for the AI customer service system."""

from pathlib import Path
import re
import csv
import io
import json
import hashlib
from typing import Optional

import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from pypdf import PdfReader
from google import genai
from google.genai import types
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from src.api.storage import EMBED_DIMENSIONS, build_stores
from src.llm import LLMMessage, get_llm_client


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI customer service API",
)

WEB_DIR = Path(__file__).parent / "static"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".pdf"}

# Serverless filesystems are read-only apart from a scratch directory, so fall
# back to one when the project directory cannot be written to.
try:
    KNOWLEDGE_DIR = Path("data/knowledge_base")
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR = Path("data/chroma")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    scratch = Path(tempfile.gettempdir()) / "support-desk-ai"
    KNOWLEDGE_DIR = scratch / "knowledge_base"
    CHROMA_DIR = scratch / "chroma"
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

document_store, vector_store = build_stores(
    KNOWLEDGE_DIR, CHROMA_DIR, SUPPORTED_EXTENSIONS, settings
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


# Serve the pages without caching so a plain reload always picks up the
# current HTML, CSS and JS instead of a stale copy held by the browser.
NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}


@app.get("/", include_in_schema=False)
async def website() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers=NO_CACHE)


@app.get("/chat", include_in_schema=False)
async def chat_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers=NO_CACHE)


@app.get("/admin", include_in_schema=False)
async def admin_page() -> RedirectResponse:
    """Uploading now lives in the single-screen workspace; keep the old link working."""
    return RedirectResponse(url="/", status_code=307)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    active_file: Optional[str] = Field(
        default=None,
        description="Document currently open in the viewer; its excerpts are prioritised.",
    )


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    total_tokens: int


def extract_document(filename: str, data: bytes) -> str:
    """Turn raw uploaded bytes into indexable text."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(
            f"[Page {i}]\n{page.extract_text() or ''}"
            for i, page in enumerate(reader.pages, 1)
        )
    raw = data.decode("utf-8", errors="ignore")
    if suffix == ".csv":
        rows = list(csv.DictReader(io.StringIO(raw)))
        return "\n\n".join(f"[CSV record {i}]\n" + "\n".join(f"{k}: {v}" for k, v in row.items() if v) for i, row in enumerate(rows, 1))
    if suffix == ".json":
        try:
            return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return raw
    return raw


async def embed(text: str, task_type: str) -> list[float]:
    client = genai.Client(api_key=settings.llm.gemini.api_key.get_secret_value())
    result = await client.aio.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=EMBED_DIMENSIONS
        ),
    )
    return result.embeddings[0].values


CHUNK_TARGET = 1200      # characters per chunk - small enough to stay specific
CHUNK_OVERLAP = 200      # carry-over so facts spanning a boundary are not lost
CHUNK_MIN = 80           # below this a fragment is page furniture, not content


def strip_boilerplate(text: str) -> str:
    """Remove running headers/footers that repeat on most pages of a PDF.

    These short repeated lines otherwise become their own chunks and match
    almost any query weakly, crowding real content out of the results.
    """
    lines = text.split("\n")
    pages = max(1, text.count("[Page "))
    if pages < 3:
        return text

    counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if 0 < len(stripped) < 90 and not stripped.startswith("[Page "):
            counts[stripped] = counts.get(stripped, 0) + 1

    # A line repeated on at least half the pages is furniture.
    repeated = {line for line, n in counts.items() if n >= max(3, pages // 2)}
    if not repeated:
        return text
    return "\n".join(line for line in lines if line.strip() not in repeated)


def chunk_text(text: str) -> list[str]:
    """Split into overlapping chunks of roughly CHUNK_TARGET characters.

    Paragraphs are the unit of assembly, so chunks stay semantically coherent;
    oversized paragraphs are split further so no single chunk swallows a whole
    section and dilutes its embedding.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    units: list[str] = []
    for para in paragraphs:
        if len(para) <= CHUNK_TARGET:
            units.append(para)
            continue
        # Split a long paragraph on sentence boundaries.
        sentences = re.split(r"(?<=[.!?])\s+", para)
        buffer = ""
        for sentence in sentences:
            if len(buffer) + len(sentence) + 1 > CHUNK_TARGET and buffer:
                units.append(buffer.strip())
                buffer = sentence
            else:
                buffer = f"{buffer} {sentence}".strip()
        if buffer:
            units.append(buffer.strip())

    chunks: list[str] = []
    current = ""
    for unit in units:
        if len(current) + len(unit) + 2 > CHUNK_TARGET and current:
            chunks.append(current.strip())
            # Start the next chunk with the tail of this one for continuity.
            current = (current[-CHUNK_OVERLAP:] + "\n\n" + unit) if CHUNK_OVERLAP else unit
        else:
            current = f"{current}\n\n{unit}".strip()
    if current.strip():
        chunks.append(current.strip())

    # Keep short chunks only when nothing else survived.
    filtered = [c for c in chunks if len(c) >= CHUNK_MIN]
    return filtered or chunks


async def index_file(filename: str, data: bytes) -> int:
    text = strip_boilerplate(extract_document(filename, data))
    chunks = chunk_text(text)
    # Drop any previous chunks for this file so re-uploads don't leave stale ones behind.
    vector_store.delete_file(filename)
    if not chunks:
        return 0
    ids = [hashlib.sha1(f"{filename}:{i}".encode()).hexdigest() for i in range(len(chunks))]
    vectors = [await embed(chunk, "RETRIEVAL_DOCUMENT") for chunk in chunks]
    vector_store.upsert(ids=ids, documents=chunks, embeddings=vectors, file=filename)
    return len(chunks)


def format_excerpts(rows: list[tuple[str, str]]) -> list[str]:
    return [f"[{file or 'knowledge base'}]\n{text}" for file, text in rows]


async def ensure_indexed() -> None:
    """Index any stored document that is missing from the vector store."""
    if vector_store.count():
        return
    for filename in await document_store.list():
        data = await document_store.get(filename)
        if data:
            await index_file(filename, data)


async def find_semantic_knowledge(query: str, limit: int = 14, active_file: Optional[str] = None) -> str:
    await ensure_indexed()
    if vector_store.count() == 0:
        return ""
    vector = await embed(query, "RETRIEVAL_QUERY")

    # When the user is reading a specific document, spend the whole budget on it
    # and add just two excerpts from elsewhere, so another file cannot displace
    # the document actually on screen.
    excerpts: list[str] = []
    if active_file:
        available = vector_store.count_file(active_file)
        if available:
            excerpts = format_excerpts(
                vector_store.query(vector, min(limit, available), file=active_file)
            )

        if vector_store.count() - available > 0:
            excerpts.extend(
                format_excerpts(vector_store.query(vector, 2, exclude_file=active_file))
            )
    else:
        excerpts = format_excerpts(
            vector_store.query(vector, min(limit, vector_store.count()))
        )

    # Embeddings are weak at exact tokens like section numbers ("4.1") or IDs,
    # so add any chunk that literally contains one. This keeps precise lookups
    # working alongside semantic search.
    excerpts.extend(lexical_excerpts(query, active_file, exclude=excerpts))
    return "\n\n".join(excerpts)


LEXICAL_TOKEN = re.compile(r"\b(?:\d+(?:\.\d+)+|[A-Z]{2,}-?\d+|\w*\d\w*)\b")


def lexical_excerpts(query: str, active_file: Optional[str], exclude: list[str], limit: int = 3) -> list[str]:
    """Return chunks containing a distinctive literal token from the query."""
    tokens = [t for t in LEXICAL_TOKEN.findall(query) if len(t) > 1]
    if not tokens:
        return []

    seen = "\n\n".join(exclude)
    found: list[str] = []
    for file, text in vector_store.chunks_for(active_file):
        if len(found) >= limit:
            break
        if any(token in text for token in tokens) and text not in seen:
            found.append(f"[{file or 'knowledge base'}]\n{text}")
    return found


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment.value}


@app.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)) -> dict[str, object]:
    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Supported files: .txt, .md, .csv, .json, .log, .pdf")
    data = await file.read()
    await document_store.put(filename, data)
    try:
        chunks = await index_file(filename, data)
    except Exception as exc:
        await document_store.delete(filename)
        raise HTTPException(status_code=502, detail=f"Indexing failed: {exc}") from exc
    return {"filename": filename, "status": "uploaded", "chunks": chunks}


@app.post("/knowledge/reindex")
async def reindex_knowledge() -> dict[str, object]:
    """Rebuild the vector index for every stored document."""
    rebuilt: dict[str, int] = {}
    for filename in await document_store.list():
        data = await document_store.get(filename)
        if data is not None:
            rebuilt[filename] = await index_file(filename, data)
    return {"reindexed": rebuilt, "total_chunks": sum(rebuilt.values())}


@app.get("/knowledge/status")
async def knowledge_status() -> dict[str, object]:
    files = [
        name for name in await document_store.list()
        if Path(name).suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return {"ready": bool(files), "files": files}


def validate_filename(filename: str) -> str:
    """Reject path traversal and unsupported extensions."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=404, detail="File not found")
    return filename


@app.get("/knowledge/document/{filename}")
async def knowledge_document(filename: str) -> dict[str, object]:
    """Return the extracted text of an uploaded document for side-by-side viewing."""
    name = validate_filename(filename)
    data = await document_store.get(name)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    text = extract_document(name, data)
    return {
        "filename": name,
        "content": text,
        "characters": len(text),
        "size_kb": round(len(data) / 1024, 1),
    }


@app.delete("/knowledge/document/{filename}")
async def delete_knowledge_document(filename: str) -> dict[str, str]:
    """Remove a document from storage and drop its chunks from the vector index."""
    name = validate_filename(filename)
    if await document_store.get(name) is None:
        raise HTTPException(status_code=404, detail="File not found")
    vector_store.delete_file(name)
    await document_store.delete(name)
    return {"filename": name, "status": "deleted"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Generate a customer-service response using the configured LLM provider."""
    if not await document_store.list():
        raise HTTPException(status_code=400, detail="Upload a knowledge file before chatting.")
    try:
        active_file = Path(request.active_file).name if request.active_file else None
        knowledge = await find_semantic_knowledge(request.message, active_file=active_file)
        system_prompt = request.system_prompt or "You are a helpful customer-service assistant."
        if knowledge:
            system_prompt += "\n\nUse these uploaded knowledge excerpts when relevant. If unsupported, say so clearly:\n\n" + knowledge
            if active_file:
                system_prompt += (
                    f"\n\nThe customer is currently reading '{active_file}', so prefer that document"
                    " when it answers the question. Always answer in full sentences that state the"
                    " actual information, then cite the source file in brackets at the end."
                )
        response = await get_llm_client().generate(
            messages=[LLMMessage(role="user", content=request.message)],
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    return ChatResponse(
        content=response.content,
        provider=response.provider,
        model=response.model,
        total_tokens=response.total_tokens,
    )

"""FastAPI application entrypoint for the AI customer service system."""

from pathlib import Path
import re
import csv
import io
import json
import hashlib
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pypdf import PdfReader
import chromadb
from google import genai
from google.genai import types
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from src.llm import LLMMessage, get_llm_client


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI customer service API",
)

WEB_DIR = Path(__file__).parent / "static"
KNOWLEDGE_DIR = Path("data/knowledge_base")
CHROMA_DIR = Path("data/chroma")
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
vector_db = chromadb.PersistentClient(path=str(CHROMA_DIR))
knowledge_collection = vector_db.get_or_create_collection("knowledge_base")
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".pdf"}
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


def extract_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "\n\n".join(f"[Page {i}]\n{page.extract_text() or ''}" for i, page in enumerate(PdfReader(str(path)).pages, 1))
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".csv":
        rows = list(csv.DictReader(io.StringIO(raw)))
        return "\n\n".join(f"[CSV record {i}]\n" + "\n".join(f"{k}: {v}" for k, v in row.items() if v) for i, row in enumerate(rows, 1))
    if suffix == ".json":
        try:
            return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return raw
    return raw


def find_knowledge(query: str, limit: int = 6) -> str:
    terms = set(re.findall(r"[a-zA-Z0-9]{3,}", query.lower()))
    matches: list[tuple[int, str, str]] = []
    for path in KNOWLEDGE_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        text = extract_document(path)
        for chunk in re.split(r"\n\s*\n", text):
            score = sum(term in chunk.lower() for term in terms)
            if score:
                matches.append((score, path.name, chunk.strip()[:1800]))
    matches.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(f"[{name}]\n{chunk}" for _, name, chunk in matches[:limit])


async def embed(text: str, task_type: str) -> list[float]:
    client = genai.Client(api_key=settings.llm.gemini.api_key.get_secret_value())
    result = await client.aio.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),
    )
    return result.embeddings[0].values


async def index_file(path: Path) -> int:
    text = extract_document(path)
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    # Drop any previous chunks for this file so re-uploads don't leave stale ones behind.
    stale = knowledge_collection.get(where={"file": path.name})
    if stale.get("ids"):
        knowledge_collection.delete(ids=stale["ids"])
    if not chunks:
        return 0
    ids = [hashlib.sha1(f"{path.name}:{i}".encode()).hexdigest() for i in range(len(chunks))]
    vectors = [await embed(chunk, "RETRIEVAL_DOCUMENT") for chunk in chunks]
    knowledge_collection.upsert(ids=ids, documents=chunks, embeddings=vectors, metadatas=[{"file": path.name} for _ in chunks])
    return len(chunks)


def format_excerpts(result: dict) -> list[str]:
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    return [f"[{meta.get('file', 'knowledge base')}]\n{doc}" for doc, meta in zip(documents, metadatas)]


async def find_semantic_knowledge(query: str, limit: int = 6, active_file: Optional[str] = None) -> str:
    if knowledge_collection.count() == 0:
        for path in KNOWLEDGE_DIR.iterdir():
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                await index_file(path)
    if knowledge_collection.count() == 0:
        return ""
    vector = await embed(query, "RETRIEVAL_QUERY")

    # When the user is reading a specific document, reserve most of the context
    # for that file so a large unrelated document cannot crowd it out, then top
    # up with the best matches from the rest of the knowledge base.
    excerpts: list[str] = []
    if active_file:
        focused = knowledge_collection.query(
            query_embeddings=[vector],
            n_results=max(1, limit - 2),
            where={"file": active_file},
        )
        excerpts = format_excerpts(focused)

    remaining = limit - len(excerpts)
    if remaining > 0:
        others = knowledge_collection.query(
            query_embeddings=[vector],
            n_results=remaining,
            **({"where": {"file": {"$ne": active_file}}} if active_file else {}),
        )
        excerpts.extend(format_excerpts(others))

    return "\n\n".join(excerpts)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment.value}


@app.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)) -> dict[str, object]:
    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Supported files: .txt, .md, .csv, .json, .log, .pdf")
    (KNOWLEDGE_DIR / filename).write_bytes(await file.read())
    try:
        chunks = await index_file(KNOWLEDGE_DIR / filename)
    except Exception as exc:
        (KNOWLEDGE_DIR / filename).unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=f"Indexing failed: {exc}") from exc
    return {"filename": filename, "status": "uploaded", "chunks": chunks}

@app.get("/knowledge/status")
async def knowledge_status() -> dict[str, object]:
    files = [p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return {"ready": bool(files), "files": files}


def resolve_knowledge_file(filename: str) -> Path:
    """Resolve a knowledge-base filename, rejecting anything outside KNOWLEDGE_DIR."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = KNOWLEDGE_DIR / filename
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return path


@app.get("/knowledge/document/{filename}")
async def knowledge_document(filename: str) -> dict[str, object]:
    """Return the extracted text of an uploaded document for side-by-side viewing."""
    path = resolve_knowledge_file(filename)
    text = extract_document(path)
    return {
        "filename": path.name,
        "content": text,
        "characters": len(text),
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


@app.delete("/knowledge/document/{filename}")
async def delete_knowledge_document(filename: str) -> dict[str, str]:
    """Remove a document from disk and drop its chunks from the vector index."""
    path = resolve_knowledge_file(filename)
    existing = knowledge_collection.get(where={"file": path.name})
    if existing.get("ids"):
        knowledge_collection.delete(ids=existing["ids"])
    path.unlink()
    return {"filename": path.name, "status": "deleted"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Generate a customer-service response using the configured LLM provider."""
    if not any(
        path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        for path in KNOWLEDGE_DIR.iterdir()
    ):
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

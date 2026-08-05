"""Storage backends for documents and vectors.

The app runs in two very different environments:

* Locally, the filesystem is writable and a directory of files plus an on-disk
  index is the simplest thing that works.
* On Vercel, only ``/tmp`` is writable and it does not survive between
  invocations, so both the uploaded files and the vector index must live in
  hosted services.

Both cases are expressed through the same two interfaces below, selected from
configuration, so ``src/api/main.py`` never needs to know which one is active.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Protocol

import httpx

BLOB_API = "https://blob.vercel-storage.com"


# ===========================================================================
# Document storage
# ===========================================================================

class DocumentStore(Protocol):
    """Stores the raw bytes of uploaded documents."""

    async def put(self, filename: str, data: bytes) -> None: ...
    async def get(self, filename: str) -> Optional[bytes]: ...
    async def delete(self, filename: str) -> None: ...
    async def list(self) -> list[str]: ...


class LocalDocumentStore:
    """Documents on the local filesystem (development)."""

    def __init__(self, directory: Path, extensions: set[str]) -> None:
        self.directory = directory
        self.extensions = extensions
        self.directory.mkdir(parents=True, exist_ok=True)

    async def put(self, filename: str, data: bytes) -> None:
        (self.directory / filename).write_bytes(data)

    async def get(self, filename: str) -> Optional[bytes]:
        path = self.directory / filename
        return path.read_bytes() if path.is_file() else None

    async def delete(self, filename: str) -> None:
        (self.directory / filename).unlink(missing_ok=True)

    async def list(self) -> list[str]:
        if not self.directory.is_dir():
            return []
        return [
            p.name for p in sorted(self.directory.iterdir())
            if p.is_file() and p.suffix.lower() in self.extensions
        ]


class BlobDocumentStore:
    """Documents in Vercel Blob (serverless).

    Files are stored under a ``knowledge/`` prefix with ``addRandomSuffix``
    disabled, so a filename maps to exactly one blob and re-uploading replaces
    it rather than accumulating copies.
    """

    def __init__(self, token: str, prefix: str = "knowledge/") -> None:
        self.token = token
        self.prefix = prefix

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.token}", "x-api-version": "7"}

    async def put(self, filename: str, data: bytes) -> None:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.put(
                f"{BLOB_API}/{self.prefix}{filename}",
                content=data,
                headers={
                    **self._headers(),
                    "x-add-random-suffix": "0",
                    "x-allow-overwrite": "1",
                    "x-content-type": "application/octet-stream",
                },
            )
            response.raise_for_status()

    async def _url_for(self, filename: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{BLOB_API}/",
                params={"prefix": f"{self.prefix}{filename}", "limit": "1"},
                headers=self._headers(),
            )
            response.raise_for_status()
            blobs = response.json().get("blobs", [])
        for blob in blobs:
            if blob.get("pathname") == f"{self.prefix}{filename}":
                return blob.get("url")
        return None

    async def get(self, filename: str) -> Optional[bytes]:
        url = await self._url_for(filename)
        if not url:
            return None
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.content

    async def delete(self, filename: str) -> None:
        url = await self._url_for(filename)
        if not url:
            return
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{BLOB_API}/delete",
                json={"urls": [url]},
                headers={**self._headers(), "content-type": "application/json"},
            )
            response.raise_for_status()

    async def list(self) -> list[str]:
        names: list[str] = []
        cursor: Optional[str] = None
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                params = {"prefix": self.prefix, "limit": "1000"}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BLOB_API}/", params=params, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
                for blob in payload.get("blobs", []):
                    pathname = blob.get("pathname", "")
                    if pathname.startswith(self.prefix):
                        names.append(pathname[len(self.prefix):])
                cursor = payload.get("cursor")
                if not payload.get("hasMore") or not cursor:
                    break
        return sorted(n for n in names if n)


# ===========================================================================
# Vector storage
# ===========================================================================

class VectorStore(Protocol):
    """Stores chunk embeddings and answers similarity queries."""

    def upsert(self, ids: list[str], documents: list[str], embeddings: list[list[float]],
               file: str) -> None: ...
    def delete_file(self, file: str) -> None: ...
    def count(self) -> int: ...
    def count_file(self, file: str) -> int: ...
    def chunks_for(self, file: Optional[str]) -> list[tuple[str, str]]: ...
    def query(self, embedding: list[float], limit: int, file: Optional[str] = None,
              exclude_file: Optional[str] = None) -> list[tuple[str, str]]: ...


class ChromaVectorStore:
    """Local ChromaDB index (development)."""

    def __init__(self, path: Path, collection: str) -> None:
        import chromadb  # imported lazily so serverless never loads it

        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(collection)

    def upsert(self, ids, documents, embeddings, file):
        self.collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings,
            metadatas=[{"file": file} for _ in documents],
        )

    def delete_file(self, file):
        existing = self.collection.get(where={"file": file})
        if existing.get("ids"):
            self.collection.delete(ids=existing["ids"])

    def count(self):
        return self.collection.count()

    def count_file(self, file):
        return len(self.collection.get(where={"file": file}).get("ids", []))

    def chunks_for(self, file):
        stored = self.collection.get(where={"file": file}) if file else self.collection.get()
        documents = stored.get("documents") or []
        metadatas = stored.get("metadatas") or []
        return [(m.get("file", ""), d) for d, m in zip(documents, metadatas)]

    def query(self, embedding, limit, file=None, exclude_file=None):
        where = None
        if file:
            where = {"file": file}
        elif exclude_file:
            where = {"file": {"$ne": exclude_file}}
        result = self.collection.query(
            query_embeddings=[embedding], n_results=max(1, limit), **({"where": where} if where else {})
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [(m.get("file", ""), d) for d, m in zip(documents, metadatas)]


class QdrantVectorStore:
    """Hosted Qdrant collection (serverless)."""

    def __init__(self, url: str, api_key: Optional[str], collection: str, vector_size: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels

        self.models = qmodels
        self.collection = collection
        self.client = QdrantClient(url=url, api_key=api_key, timeout=60)

        existing = {c.name for c in self.client.get_collections().collections}
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=qmodels.VectorParams(
                    size=vector_size, distance=qmodels.Distance.COSINE
                ),
            )
        # Payload index makes filtering by file fast and is required for
        # filtered queries on larger collections.
        try:
            self.client.create_payload_index(
                collection_name=collection,
                field_name="file",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass  # already exists

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        # Qdrant accepts UUIDs or unsigned integers; our ids are sha1 hex, so
        # format them as a UUID string.
        h = chunk_id[:32].ljust(32, "0")
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

    def upsert(self, ids, documents, embeddings, file):
        points = [
            self.models.PointStruct(
                id=self._point_id(i), vector=v, payload={"file": file, "text": d}
            )
            for i, d, v in zip(ids, documents, embeddings)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def _file_filter(self, file: str, negate: bool = False):
        condition = self.models.FieldCondition(
            key="file", match=self.models.MatchValue(value=file)
        )
        if negate:
            return self.models.Filter(must_not=[condition])
        return self.models.Filter(must=[condition])

    def delete_file(self, file):
        self.client.delete(
            collection_name=self.collection,
            points_selector=self.models.FilterSelector(filter=self._file_filter(file)),
            wait=True,
        )

    def count(self):
        return self.client.count(collection_name=self.collection, exact=True).count

    def count_file(self, file):
        return self.client.count(
            collection_name=self.collection, count_filter=self._file_filter(file), exact=True
        ).count

    def chunks_for(self, file):
        results: list[tuple[str, str]] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=self._file_filter(file) if file else None,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            results.extend(
                (p.payload.get("file", ""), p.payload.get("text", "")) for p in points
            )
            if offset is None:
                break
        return results

    def query(self, embedding, limit, file=None, exclude_file=None):
        query_filter = None
        if file:
            query_filter = self._file_filter(file)
        elif exclude_file:
            query_filter = self._file_filter(exclude_file, negate=True)
        # query_points replaced the removed search() in qdrant-client 1.10+.
        response = self.client.query_points(
            collection_name=self.collection,
            query=embedding,
            query_filter=query_filter,
            limit=max(1, limit),
            with_payload=True,
        )
        return [
            (p.payload.get("file", ""), p.payload.get("text", ""))
            for p in response.points
        ]


# ===========================================================================
# Selection
# ===========================================================================

def build_stores(knowledge_dir: Path, chroma_dir: Path, extensions: set[str], settings):
    """Pick the backends that suit the current environment.

    Vercel Blob and Qdrant are used when their credentials are present;
    otherwise the local filesystem and ChromaDB are used.
    """
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    documents: DocumentStore = (
        BlobDocumentStore(blob_token) if blob_token
        else LocalDocumentStore(knowledge_dir, extensions)
    )

    qdrant = getattr(settings.vector_db, "qdrant", None)
    if qdrant and getattr(qdrant, "url", None):
        api_key = qdrant.api_key.get_secret_value() if qdrant.api_key else None
        vectors: VectorStore = QdrantVectorStore(
            url=qdrant.url,
            api_key=api_key,
            collection=qdrant.collection_name,
            vector_size=EMBED_DIMENSIONS,
        )
    else:
        vectors = ChromaVectorStore(chroma_dir, "knowledge_base")

    return documents, vectors


# Gemini embedding dimensions used throughout the app.
EMBED_DIMENSIONS = 768

"""Memory routes for long-term knowledge storage and retrieval."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from database.connection import get_db
from database.models import MemoryEntry, User
from backend.schemas.schemas import MemoryCreate, MemoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["Memory"])

_chroma_client = None
_chroma_lock = threading.Lock()


def _get_chroma():
    """Get or lazily create the shared ChromaDB client (thread-safe)."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client
    with _chroma_lock:
        if _chroma_client is not None:
            return _chroma_client
        import chromadb
        from config.settings import settings
        _chroma_client = chromadb.PersistentClient(path=settings.chromadb_persist_directory)
        return _chroma_client


def _get_collection():
    return _get_chroma().get_or_create_collection("jarvis_memory")


def _create_embedding_sync(text: str) -> Optional[str]:
    try:
        embedding_id = str(uuid.uuid4())
        _get_collection().add(ids=[embedding_id], documents=[text])
        return embedding_id
    except Exception as exc:
        logger.warning("ChromaDB embedding failed (non-fatal): %s", exc)
        return None


def _search_embeddings_sync(query: str, n_results: int = 10) -> List[Dict[str, Any]]:
    try:
        results = _get_collection().query(query_texts=[query], n_results=n_results)
        matches = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                matches.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })
        return matches
    except Exception as exc:
        logger.warning("ChromaDB search failed: %s", exc)
        return []


def _delete_embedding_sync(embedding_id: str) -> None:
    try:
        _get_collection().delete(ids=[embedding_id])
    except Exception as exc:
        logger.warning("ChromaDB delete failed: %s", exc)


async def _create_embedding(text: str) -> Optional[str]:
    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _create_embedding_sync, text),
            timeout=15,
        )
    except asyncio.TimeoutError:
        logger.warning("ChromaDB embedding timed out (non-fatal)")
        return None


async def _search_embeddings(query: str, n_results: int = 10) -> List[Dict[str, Any]]:
    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _search_embeddings_sync, query, n_results),
            timeout=15,
        )
    except asyncio.TimeoutError:
        logger.warning("ChromaDB search timed out")
        return []


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def add_memory(
    body: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new memory entry with optional vector embedding."""
    embedding_id = await _create_embedding(body.content)
    entry = MemoryEntry(
        user_id=current_user.id,
        content=body.content,
        category=body.category,
        metadata_=body.metadata,
        embedding_id=embedding_id,
        expires_at=body.expires_at,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return MemoryResponse(
        id=entry.id,
        user_id=entry.user_id,
        content=entry.content,
        category=entry.category,
        metadata=entry.metadata_,
        embedding_id=entry.embedding_id,
        created_at=entry.created_at,
        expires_at=entry.expires_at,
    )


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_memory(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic search across memories using vector embeddings + DB fallback."""
    # Try vector search first
    vector_results = await _search_embeddings(q, n_results=limit)

    # Also do DB text search as fallback / supplement
    pattern = f"%{q}%"
    db_q = (
        select(MemoryEntry)
        .where(
            MemoryEntry.user_id == current_user.id,
            MemoryEntry.content.ilike(pattern),
        )
        .order_by(MemoryEntry.created_at.desc())
        .limit(limit)
    )
    db_result = await db.execute(db_q)
    db_entries = db_result.scalars().all()

    combined = []
    seen = set()
    for vr in vector_results:
        combined.append({"source": "vector", **vr})
        seen.add(vr["id"])
    for entry in db_entries:
        combined.append({
            "source": "database",
            "id": str(entry.id),
            "content": entry.content,
            "category": entry.category,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })
    return combined[:limit]


@router.get("/categories", response_model=List[str])
async def list_memory_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all distinct memory categories for the user."""
    q = (
        select(MemoryEntry.category)
        .where(
            MemoryEntry.user_id == current_user.id,
            MemoryEntry.category.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(q)
    return [row[0] for row in result.all()]


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a memory entry and its embedding."""
    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.id == memory_id, MemoryEntry.user_id == current_user.id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    if entry.embedding_id:
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _delete_embedding_sync, entry.embedding_id),
                timeout=15,
            )
        except asyncio.TimeoutError:
            logger.warning("ChromaDB delete timed out (non-fatal)")
    await db.delete(entry)

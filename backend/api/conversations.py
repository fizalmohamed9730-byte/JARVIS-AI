"""Conversation API routes."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.auth import get_current_user
from database.connection import get_db
from database.models import Conversation, Message, MessageRole, User
from backend.schemas.schemas import (
    ConversationCreate,
    ConversationList,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=ConversationList)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversations for the current user with pagination."""
    offset = (page - 1) * page_size
    count_q = select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = result.scalars().all()
    return ConversationList(
        items=[ConversationResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation."""
    conv = Conversation(user_id=current_user.id, title=body.title, summary=body.summary)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single conversation by ID."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    await db.delete(conv)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all messages in a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msg_q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msg_result = await db.execute(msg_q)
    return msg_result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: int,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a user message and stream an assistant response via AI service.

    If a WebSocket connection exists for this user, chunks are pushed in real-time.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    user_msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.user,
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()
    await db.refresh(user_msg)

    history_q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history_result = await db.execute(history_q)
    history = history_result.scalars().all()

    messages_for_ai = [{"role": m.role.value, "content": m.content} for m in history]

    try:
        from backend.services.ai_service import ai_service
        from backend.services.websocket_manager import ws_manager

        full_response = ""
        async for chunk in ai_service.stream_chat(messages_for_ai):
            full_response += chunk
            try:
                await ws_manager.send_to_user(current_user.id, {
                    "type": "stream_chunk",
                    "conversation_id": conversation_id,
                    "content": chunk,
                    "accumulated": full_response,
                })
            except Exception:
                pass

        try:
            await ws_manager.send_to_user(current_user.id, {
                "type": "stream_end",
                "conversation_id": conversation_id,
                "content": full_response,
            })
        except Exception:
            pass

        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content=full_response,
            model_used=ai_service.preferred_model,
        )
        db.add(assistant_msg)
        await db.flush()
        await db.refresh(assistant_msg)
        return assistant_msg
    except Exception as exc:
        logger.error("AI response failed: %s", exc)
        fallback_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content="I'm sorry, I encountered an error processing your request. Please try again.",
        )
        db.add(fallback_msg)
        await db.flush()
        await db.refresh(fallback_msg)
        return fallback_msg

"""WebSocket connection manager for real-time communication."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections, rooms, and broadcasting."""

    def __init__(self):
        self._connections: Dict[int, WebSocket] = {}
        self._rooms: Dict[str, Set[int]] = {}
        self._user_rooms: Dict[int, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections[user_id] = websocket
        logger.info("WebSocket connected: user %s", user_id)

    def disconnect(self, user_id: int) -> None:
        """Remove a WebSocket connection."""
        self._connections.pop(user_id, None)
        for room_id in self._user_rooms.pop(user_id, set()):
            room = self._rooms.get(room_id, set())
            room.discard(user_id)
            if not room:
                del self._rooms[room_id]
        logger.info("WebSocket disconnected: user %s", user_id)

    async def send_to_user(self, user_id: int, data: dict) -> bool:
        """Send a JSON message to a specific user."""
        ws = self._connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception as exc:
            logger.error("Failed to send to user %s: %s", user_id, exc)
            self.disconnect(user_id)
            return False

    async def broadcast(self, data: dict, exclude: Optional[int] = None) -> int:
        """Send a JSON message to all connected clients. Returns count sent."""
        sent = 0
        for uid, ws in list(self._connections.items()):
            if uid == exclude:
                continue
            try:
                await ws.send_json(data)
                sent += 1
            except Exception:
                self.disconnect(uid)
        return sent

    def join_room(self, user_id: int, room_id: str) -> None:
        """Add a user to a named room."""
        self._rooms.setdefault(room_id, set()).add(user_id)
        self._user_rooms.setdefault(user_id, set()).add(room_id)

    def leave_room(self, user_id: int, room_id: str) -> None:
        """Remove a user from a named room."""
        room = self._rooms.get(room_id, set())
        room.discard(user_id)
        if not room:
            self._rooms.pop(room_id, None)
        self._user_rooms.get(user_id, set()).discard(room_id)

    async def broadcast_to_room(self, room_id: str, data: dict, exclude: Optional[int] = None) -> int:
        """Send a JSON message to all users in a room."""
        room = self._rooms.get(room_id, set())
        sent = 0
        for uid in list(room):
            if uid == exclude:
                continue
            if await self.send_to_user(uid, data):
                sent += 1
        return sent

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def get_room_members(self, room_id: str) -> List[int]:
        return list(self._rooms.get(room_id, set()))

    def is_connected(self, user_id: int) -> bool:
        return user_id in self._connections


ws_manager = ConnectionManager()

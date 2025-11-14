import asyncio
import logging
from typing import Dict, List, Tuple

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages user-specific WebSocket connections."""

    def __init__(self):
        """Initializes the manager with a dictionary for active connections and a lock."""
        self.active_connections: Dict[int, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accepts and stores a new WebSocket connection for a specific user."""
        await websocket.accept()
        async with self.lock:
            self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket.")

    async def disconnect(self, user_id: int):
        """Removes a WebSocket connection for a specific user."""
        async with self.lock:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                logger.info(f"Disconnected and removed WebSocket for user {user_id}.")

    async def send_personal_message(self, message: str, user_id: int):
        """Sends a message to a single user's WebSocket connection."""
        websocket: WebSocket | None = None
        async with self.lock:
            websocket = self.active_connections.get(user_id)

        if websocket:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                logger.warning(f"WebSocket for user {user_id} disconnected during send.")
                await self.disconnect(user_id)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
        else:
            logger.warning(f"WebSocket connection for user {user_id} not found.")

    async def broadcast(self, message: str):
        """Broadcasts a message to all active WebSocket connections."""
        disconnected_user_ids: List[int] = []
        connections_to_iterate: List[Tuple[int, WebSocket]] = []

        async with self.lock:
            # Create a copy to iterate over, avoiding modification during iteration
            connections_to_iterate = list(self.active_connections.items())

        for user_id, websocket in connections_to_iterate:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                disconnected_user_ids.append(user_id)
                logger.warning(f"WebSocket for user {user_id} disconnected during broadcast.")
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")

        # Clean up any disconnected clients found during the broadcast
        if disconnected_user_ids:
            for user_id in disconnected_user_ids:
                await self.disconnect(user_id)


# Singleton instance of the ConnectionManager
manager = ConnectionManager()

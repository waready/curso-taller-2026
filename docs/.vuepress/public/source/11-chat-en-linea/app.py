from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Chat en linea")
BASE_DIR = Path(__file__).parent
COLORS = ("#ffb347", "#61d4b3", "#7db7ff", "#ff8f8f", "#c9a7ff", "#f4df66")
MAX_HISTORY = 50


def clean_text(value: object, fallback: str, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return text or fallback


class Room:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}
        self.history: list[dict] = []


class ChatManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.room_by_socket: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def join(self, websocket: WebSocket, name: object, room_name: object) -> tuple[dict, str]:
        room_key = clean_text(room_name, "General", 24)
        room = self.rooms.setdefault(room_key, Room())
        user = {
            "id": uuid4().hex[:8],
            "name": clean_text(name, "Invitado", 24),
            "color": COLORS[len(room.clients) % len(COLORS)],
        }
        room.clients[websocket] = user
        self.room_by_socket[websocket] = room_key
        return user, room_key

    def room_for(self, websocket: WebSocket) -> tuple[str, Room] | None:
        room_key = self.room_by_socket.get(websocket)
        room = self.rooms.get(room_key) if room_key else None
        return (room_key, room) if room_key and room else None

    def disconnect(self, websocket: WebSocket) -> tuple[str | None, dict | None]:
        room_key = self.room_by_socket.pop(websocket, None)
        room = self.rooms.get(room_key) if room_key else None
        if not room:
            return None, None
        user = room.clients.pop(websocket, None)
        if not room.clients:
            self.rooms.pop(room_key, None)
        return room_key, user

    async def broadcast(
        self,
        room_key: str,
        event: dict,
        exclude: WebSocket | None = None,
    ) -> None:
        room = self.rooms.get(room_key)
        if not room:
            return
        disconnected: list[WebSocket] = []
        for client in list(room.clients):
            if client is exclude:
                continue
            try:
                await client.send_json(event)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(client)
        for client in disconnected:
            self.disconnect(client)

    async def presence(self, room_key: str) -> None:
        room = self.rooms.get(room_key)
        if not room:
            return
        await self.broadcast(
            room_key,
            {
                "type": "presence",
                "count": len(room.clients),
                "users": list(room.clients.values()),
            },
        )


manager = ChatManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def chat_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        if not isinstance(first, dict) or first.get("type") != "join":
            await websocket.send_json({"type": "error", "message": "Envia primero tu nombre y sala."})
            return

        user, room_key = await manager.join(websocket, first.get("name"), first.get("room"))
        room = manager.rooms[room_key]
        await websocket.send_json(
            {
                "type": "welcome",
                "user": user,
                "room": room_key,
                "history": room.history,
            }
        )
        await manager.broadcast(
            room_key,
            {
                "type": "system",
                "text": f"{user['name']} entro a la sala",
                "time": datetime.now().strftime("%H:%M"),
            },
        )
        await manager.presence(room_key)

        while True:
            event = await websocket.receive_json()
            active_room = manager.room_for(websocket)
            if not isinstance(event, dict) or not active_room:
                continue
            room_key, room = active_room
            event_type = event.get("type")

            if event_type == "message":
                text = clean_text(event.get("text"), "", 500)
                if not text:
                    continue
                message = {
                    "type": "message",
                    "id": uuid4().hex[:10],
                    "user_id": user["id"],
                    "user": user["name"],
                    "color": user["color"],
                    "text": text,
                    "time": datetime.now().strftime("%H:%M"),
                }
                room.history.append(message)
                room.history = room.history[-MAX_HISTORY:]
                await manager.broadcast(room_key, message)
            elif event_type == "typing":
                await manager.broadcast(
                    room_key,
                    {
                        "type": "typing",
                        "user_id": user["id"],
                        "user": user["name"],
                        "active": bool(event.get("active")),
                    },
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        pass
    finally:
        room_key, user = manager.disconnect(websocket)
        if room_key and user:
            await manager.broadcast(
                room_key,
                {
                    "type": "system",
                    "text": f"{user['name']} salio de la sala",
                    "time": datetime.now().strftime("%H:%M"),
                },
            )
            await manager.presence(room_key)

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Cursor Party")
BASE_DIR = Path(__file__).parent
COLORS = ("#22d3ee", "#a78bfa", "#fb7185", "#facc15", "#4ade80", "#fb923c")
MAX_LINES = 500


def clean_label(value: object, fallback: str, limit: int) -> str:
    label = " ".join(str(value or "").split())[:limit]
    return label or fallback


def percentage(value: object, fallback: float = 50) -> float:
    try:
        return max(0, min(100, float(value)))
    except (TypeError, ValueError):
        return fallback


class PartyRoom:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}
        self.lines: list[dict] = []
        self.owner_id: str | None = None
        self.line_revision = 0


class CursorManager:
    def __init__(self) -> None:
        self.rooms: dict[str, PartyRoom] = {}
        self.room_by_socket: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def join(self, websocket: WebSocket, name: object, room_name: object) -> tuple[dict, str]:
        room_key = clean_label(room_name, "Sala general", 24)
        room = self.rooms.setdefault(room_key, PartyRoom())
        cursor_id = uuid4().hex[:8]
        cursor = {
            "id": cursor_id,
            "name": clean_label(name, "Anonimo", 18),
            "color": COLORS[len(room.clients) % len(COLORS)],
            "x": 50,
            "y": 50,
        }
        room.clients[websocket] = cursor
        self.room_by_socket[websocket] = room_key
        if room.owner_id is None:
            room.owner_id = cursor_id
        return cursor, room_key

    def room_for(self, websocket: WebSocket) -> tuple[str, PartyRoom] | None:
        room_key = self.room_by_socket.get(websocket)
        if not room_key:
            return None
        room = self.rooms.get(room_key)
        return (room_key, room) if room else None

    def disconnect(self, websocket: WebSocket) -> str | None:
        room_key = self.room_by_socket.pop(websocket, None)
        if not room_key:
            return None

        room = self.rooms.get(room_key)
        if not room:
            return None
        cursor = room.clients.pop(websocket, None)
        if cursor and room.owner_id == cursor["id"]:
            next_cursor = next(iter(room.clients.values()), None)
            room.owner_id = next_cursor["id"] if next_cursor else None
        if not room.clients:
            self.rooms.pop(room_key, None)
            return None
        return room_key

    async def send_error(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_json({"type": "error", "message": message})

    async def broadcast(self, room_key: str) -> None:
        room = self.rooms.get(room_key)
        if not room:
            return
        event = {
            "type": "state",
            "room": room_key,
            "owner_id": room.owner_id,
            "cursors": list(room.clients.values()),
            "lines": room.lines,
            "line_revision": room.line_revision,
        }
        disconnected: list[WebSocket] = []
        for client in list(room.clients):
            try:
                await client.send_json(event)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(client)
        for client in disconnected:
            self.disconnect(client)


manager = CursorManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def cursor_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        if not isinstance(first, dict) or first.get("type") != "join":
            await manager.send_error(websocket, "Envia primero tu nombre y sala.")
            return

        cursor, room_key = await manager.join(websocket, first.get("name"), first.get("room"))
        await websocket.send_json(
            {
                "type": "welcome",
                "id": cursor["id"],
                "color": cursor["color"],
                "room": room_key,
                "is_owner": cursor["id"] == manager.rooms[room_key].owner_id,
            }
        )
        await manager.broadcast(room_key)

        while True:
            event = await websocket.receive_json()
            if not isinstance(event, dict):
                await manager.send_error(websocket, "El evento debe ser un objeto JSON.")
                continue

            active_room = manager.room_for(websocket)
            if not active_room:
                return
            room_key, room = active_room
            own_cursor = room.clients[websocket]
            event_type = event.get("type")

            if event_type == "move":
                own_cursor["x"] = percentage(event.get("x"))
                own_cursor["y"] = percentage(event.get("y"))
                await manager.broadcast(room_key)
            elif event_type == "draw":
                line = {
                    "x1": percentage(event.get("x1"), 0),
                    "y1": percentage(event.get("y1"), 0),
                    "x2": percentage(event.get("x2"), 0),
                    "y2": percentage(event.get("y2"), 0),
                    "width": max(0.2, min(1.6, percentage(event.get("width"), 0.45))),
                    "color": own_cursor["color"],
                    "author_id": own_cursor["id"],
                }
                room.lines.append(line)
                room.lines = room.lines[-MAX_LINES:]
                room.line_revision += 1
                await manager.broadcast(room_key)
            elif event_type == "undo":
                for index in range(len(room.lines) - 1, -1, -1):
                    if room.lines[index]["author_id"] == own_cursor["id"]:
                        room.lines.pop(index)
                        room.line_revision += 1
                        await manager.broadcast(room_key)
                        break
            elif event_type == "reset":
                if room.owner_id != own_cursor["id"]:
                    await manager.send_error(websocket, "Solo quien creo la sala puede limpiar la pizarra.")
                    continue
                room.lines.clear()
                room.line_revision += 1
                await manager.broadcast(room_key)
            else:
                await manager.send_error(websocket, "Evento no reconocido.")
    except WebSocketDisconnect:
        pass
    finally:
        room_key = manager.disconnect(websocket)
        if room_key:
            await manager.broadcast(room_key)

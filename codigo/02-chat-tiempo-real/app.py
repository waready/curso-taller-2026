from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Chat en tiempo real")
BASE_DIR = Path(__file__).parent


class ChatManager:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def send(self, websocket: WebSocket, event: dict) -> None:
        await websocket.send_json(event)

    async def broadcast(self, event: dict, exclude: WebSocket | None = None) -> None:
        disconnected: list[WebSocket] = []
        for client in self.clients:
            if client is exclude:
                continue
            try:
                await client.send_json(event)
            except RuntimeError:
                disconnected.append(client)
        for client in disconnected:
            self.clients.pop(client, None)

    async def presence(self) -> None:
        await self.broadcast(
            {
                "type": "presence",
                "count": len(self.clients),
                "users": list(self.clients.values()),
            }
        )


manager = ChatManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def chat(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    username = "Anónimo"
    try:
        first_event = await websocket.receive_json()
        username = str(first_event.get("user", "")).strip()[:24]
        if not username:
            await websocket.close(code=1008, reason="Nombre requerido")
            return

        manager.clients[websocket] = username
        await manager.broadcast(
            {"type": "system", "text": f"{username} entró al chat"}
        )
        await manager.presence()

        while True:
            event = await websocket.receive_json()
            event_type = event.get("type")

            if event_type == "message":
                text = str(event.get("text", "")).strip()[:300]
                if text:
                    await manager.broadcast(
                        {
                            "type": "message",
                            "user": username,
                            "text": text,
                            "time": datetime.now().strftime("%H:%M"),
                        }
                    )
            elif event_type == "typing":
                await manager.broadcast(
                    {
                        "type": "typing",
                        "user": username,
                        "active": bool(event.get("active")),
                    },
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        pass
    finally:
        was_connected = manager.clients.pop(websocket, None)
        if was_connected:
            await manager.broadcast(
                {"type": "system", "text": f"{username} salió del chat"}
            )
            await manager.presence()

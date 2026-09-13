from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Reacciones en vivo")
BASE_DIR = Path(__file__).parent
ALLOWED_EMOJIS = ("🔥", "👏", "🤯", "❤️")
counts = {emoji: 0 for emoji in ALLOWED_EMOJIS}


class ReactionManager:
    def __init__(self) -> None:
        self.clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.append(websocket)
        await websocket.send_json({"type": "state", "counts": counts})

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.clients:
            self.clients.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        for client in list(self.clients):
            try:
                await client.send_json(event)
            except RuntimeError:
                self.disconnect(client)


manager = ReactionManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def reactions(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await manager.broadcast({"type": "presence", "count": len(manager.clients)})
    try:
        while True:
            event = await websocket.receive_json()
            if event.get("type") == "reaction":
                emoji = event.get("emoji")
                if emoji not in ALLOWED_EMOJIS:
                    await websocket.send_json({"type": "error", "message": "Reacción no permitida"})
                    continue
                counts[emoji] += 1
                await manager.broadcast({"type": "reaction", "emoji": emoji, "counts": counts})
            elif event.get("type") == "reset":
                for emoji in counts:
                    counts[emoji] = 0
                await manager.broadcast({"type": "state", "counts": counts})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"type": "presence", "count": len(manager.clients)})

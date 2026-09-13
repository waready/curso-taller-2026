from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Encuesta Battle")
BASE_DIR = Path(__file__).parent
OPTIONS = {
    "chat": "💬 Chat",
    "wplace": "🎨 WPlace",
    "uber": "🚕 Tracker",
    "subasta": "⚡ Subasta",
}
votes: dict[str, str] = {}


class PollManager:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        voter_id = uuid4().hex[:10]
        self.clients[websocket] = voter_id
        return voter_id

    def disconnect(self, websocket: WebSocket) -> None:
        voter_id = self.clients.pop(websocket, None)
        if voter_id:
            votes.pop(voter_id, None)

    def state(self) -> dict:
        counts = {key: 0 for key in OPTIONS}
        for option in votes.values():
            counts[option] += 1
        return {
            "type": "state",
            "question": "¿Qué demo debería ganar el taller?",
            "options": OPTIONS,
            "counts": counts,
            "total": len(votes),
            "connections": len(self.clients),
        }

    async def broadcast(self) -> None:
        event = self.state()
        for client in list(self.clients):
            try:
                await client.send_json(event)
            except RuntimeError:
                self.disconnect(client)


manager = PollManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def poll_socket(websocket: WebSocket) -> None:
    voter_id = await manager.connect(websocket)
    await manager.broadcast()
    try:
        while True:
            event = await websocket.receive_json()
            option = event.get("option")
            if event.get("type") == "vote" and option in OPTIONS:
                votes[voter_id] = option
                await manager.broadcast()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast()

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="WPlace colaborativo")
BASE_DIR = Path(__file__).parent
BOARD_SIZE = 20
BACKGROUND = "#111827"
ALLOWED_COLORS = {
    "#ef4444", "#f97316", "#facc15", "#22c55e",
    "#15d1c5", "#3b82f6", "#a855f7", "#ec4899", "#f8fafc", BACKGROUND,
}
board = [BACKGROUND] * (BOARD_SIZE * BOARD_SIZE)


class BoardManager:
    def __init__(self) -> None:
        self.clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.append(websocket)
        await websocket.send_json(
            {"type": "board", "size": BOARD_SIZE, "pixels": board}
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.clients:
            self.clients.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        for client in list(self.clients):
            try:
                await client.send_json(event)
            except RuntimeError:
                self.disconnect(client)


manager = BoardManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def board_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await manager.broadcast({"type": "presence", "count": len(manager.clients)})
    try:
        while True:
            event = await websocket.receive_json()
            if event.get("type") == "reset":
                board[:] = [BACKGROUND] * (BOARD_SIZE * BOARD_SIZE)
                await manager.broadcast(
                    {"type": "board", "size": BOARD_SIZE, "pixels": board}
                )
                continue
            if event.get("type") != "paint":
                continue

            x = event.get("x")
            y = event.get("y")
            color = str(event.get("color", "")).lower()
            if not isinstance(x, int) or not isinstance(y, int):
                await websocket.send_json({"type": "error", "message": "Coordenadas inválidas"})
                continue
            if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
                await websocket.send_json({"type": "error", "message": "Píxel fuera del tablero"})
                continue
            if color not in ALLOWED_COLORS:
                await websocket.send_json({"type": "error", "message": "Color no permitido"})
                continue

            board[y * BOARD_SIZE + x] = color
            await manager.broadcast({"type": "paint", "x": x, "y": y, "color": color})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"type": "presence", "count": len(manager.clients)})

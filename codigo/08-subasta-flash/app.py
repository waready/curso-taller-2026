import asyncio
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Subasta Flash")
BASE_DIR = Path(__file__).parent
ROUND_SECONDS = 60
STARTING_PRICE = 100.0
auction = {
    "item": "Caja misteriosa del laboratorio",
    "price": STARTING_PRICE,
    "leader": "Nadie",
    "history": [],
    "ends_at": time.time() + ROUND_SECONDS,
    "last_result": "La ronda termina en un minuto.",
}


class AuctionManager:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.pop(websocket, None)

    def state(self) -> dict:
        return {"type": "state", **auction, "connections": len(self.clients)}

    async def broadcast(self) -> None:
        event = self.state()
        for client in list(self.clients):
            try:
                await client.send_json(event)
            except RuntimeError:
                self.disconnect(client)


manager = AuctionManager()


def next_round() -> None:
    if auction["leader"] == "Nadie":
        auction["last_result"] = "La ronda termino sin pujas. Nueva ronda iniciada."
    else:
        auction["last_result"] = f"Gano {auction['leader']} con S/ {auction['price']:.2f}."

    auction["price"] = STARTING_PRICE
    auction["leader"] = "Nadie"
    auction["history"] = []
    auction["ends_at"] = time.time() + ROUND_SECONDS


def reset_auction() -> None:
    auction["price"] = STARTING_PRICE
    auction["leader"] = "Nadie"
    auction["history"] = []
    auction["ends_at"] = time.time() + ROUND_SECONDS
    auction["last_result"] = "La subasta fue reiniciada. Nueva ronda de un minuto."


async def round_timer() -> None:
    while True:
        await asyncio.sleep(1)
        if time.time() >= auction["ends_at"]:
            next_round()
            await manager.broadcast()


@app.on_event("startup")
async def start_round_timer() -> None:
    asyncio.create_task(round_timer())


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def auction_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        username = str(first.get("name", "Anonimo")).strip()[:20] or "Anonimo"
        manager.clients[websocket] = username
        await manager.broadcast()

        while True:
            event = await websocket.receive_json()
            if event.get("type") == "reset":
                reset_auction()
                await manager.broadcast()
                continue
            if event.get("type") != "bid":
                continue
            try:
                amount = round(float(event.get("amount", 0)), 2)
            except (TypeError, ValueError):
                amount = 0.0

            if time.time() >= auction["ends_at"]:
                next_round()
                await manager.broadcast()
                continue
            if amount <= auction["price"]:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Tu monto debe ser mayor que el monto actual.",
                    }
                )
                continue

            auction["price"] = amount
            auction["leader"] = username
            auction["history"].insert(0, {"name": username, "amount": amount})
            auction["history"] = auction["history"][:8]
            await manager.broadcast()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast()

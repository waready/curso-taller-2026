import asyncio
import time
from pathlib import Path
from random import choice
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Cartas Casino")
BASE_DIR = Path(__file__).parent
BETS = (2.5, 5.0, 10.0, 20.0, 30.0, 50.0)
BETTING_SECONDS = 8
RESULT_SECONDS = 4
RANKS = (
    ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6), ("7", 7),
    ("8", 8), ("9", 9), ("10", 10), ("J", 11), ("Q", 12), ("K", 13), ("A", 14),
)
SUITS = ("hearts", "diamonds", "clubs", "spades")


class CasinoManager:
    def __init__(self) -> None:
        self.players: dict[WebSocket, dict] = {}
        self.round_number = 1
        self.phase = "betting"
        self.ends_at = time.time() + BETTING_SECONDS
        self.card_a: dict | None = None
        self.card_b: dict | None = None
        self.winning_side: str | None = None
        self.winners: list[dict] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def join(self, websocket: WebSocket, name: str) -> None:
        self.players[websocket] = {
            "id": uuid4().hex[:8],
            "name": name.strip()[:18] or "Jugador",
            "balance": 20.0,
            "bet": None,
            "choice": None,
            "result": None,
            "payout": 0.0,
        }

    def disconnect(self, websocket: WebSocket) -> None:
        self.players.pop(websocket, None)

    @staticmethod
    def draw_card() -> dict:
        rank, value = choice(RANKS)
        return {"rank": rank, "value": value, "suit": choice(SUITS)}

    def state(self, player: dict, error: str | None = None) -> dict:
        bettors = [item for item in self.players.values() if item["bet"] is not None]
        state = {
            "type": "state",
            "name": player["name"],
            "balance": player["balance"],
            "phase": self.phase,
            "round": self.round_number,
            "ends_at": self.ends_at,
            "players": len(self.players),
            "bet_count": len(bettors),
            "your_bet": player["bet"],
            "your_choice": player["choice"],
            "card_a": self.card_a,
            "card_b": self.card_b,
            "winning_side": self.winning_side,
            "result": player["result"],
            "payout": player["payout"],
            "winners": self.winners,
        }
        if error:
            state["error"] = error
        return state

    async def send_state(self, websocket: WebSocket, error: str | None = None) -> None:
        player = self.players.get(websocket)
        if player:
            await websocket.send_json(self.state(player, error))

    async def broadcast(self) -> None:
        for websocket, player in list(self.players.items()):
            try:
                await websocket.send_json(self.state(player))
            except RuntimeError:
                self.disconnect(websocket)

    def place_bet(self, websocket: WebSocket, amount: object, side: object) -> str | None:
        player = self.players[websocket]
        if self.phase != "betting":
            return "Las apuestas estan cerradas. Espera la siguiente ronda."
        if player["bet"] is not None:
            return "Ya registraste una apuesta para esta ronda."
        if side not in ("a", "b"):
            return "Elige Carta A o Carta B."
        try:
            bet = round(float(amount), 2)
        except (TypeError, ValueError):
            bet = 0.0
        if bet not in BETS:
            return "Elige una de las cajas de apuesta disponibles."
        if bet > player["balance"]:
            return "No tienes saldo suficiente para esa apuesta."

        player["balance"] = round(player["balance"] - bet, 2)
        player["bet"] = bet
        player["choice"] = side
        return None

    def close_bets(self) -> None:
        self.phase = "results"
        self.ends_at = time.time() + RESULT_SECONDS
        self.card_a = self.draw_card()
        self.card_b = self.draw_card()
        self.winners = []

        if self.card_a["value"] > self.card_b["value"]:
            self.winning_side = "a"
        elif self.card_b["value"] > self.card_a["value"]:
            self.winning_side = "b"
        else:
            self.winning_side = "tie"

        for player in self.players.values():
            player["result"] = None
            player["payout"] = 0.0
            if player["bet"] is None:
                continue

            if self.winning_side == "tie":
                player["balance"] = round(player["balance"] + player["bet"], 2)
                player["result"] = "tie"
            elif player["choice"] == self.winning_side:
                payout = round(player["bet"] * 2, 2)
                player["balance"] = round(player["balance"] + payout, 2)
                player["result"] = "win"
                player["payout"] = payout
                self.winners.append(
                    {
                        "name": player["name"],
                        "amount": payout,
                        "choice": player["choice"].upper(),
                    }
                )
            else:
                player["result"] = "loss"

    def start_betting(self) -> None:
        self.round_number += 1
        self.phase = "betting"
        self.ends_at = time.time() + BETTING_SECONDS
        self.card_a = None
        self.card_b = None
        self.winning_side = None
        self.winners = []
        for player in self.players.values():
            player["bet"] = None
            player["choice"] = None
            player["result"] = None
            player["payout"] = 0.0


manager = CasinoManager()


async def game_timer() -> None:
    while True:
        await asyncio.sleep(0.2)
        if time.time() < manager.ends_at:
            continue
        if manager.phase == "betting":
            manager.close_bets()
        else:
            manager.start_betting()
        await manager.broadcast()


@app.on_event("startup")
async def start_game_timer() -> None:
    asyncio.create_task(game_timer())


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def casino_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        manager.join(websocket, str(first.get("name", "Jugador")))
        await manager.broadcast()

        while True:
            event = await websocket.receive_json()
            if event.get("type") != "bet":
                continue
            error = manager.place_bet(websocket, event.get("amount"), event.get("side"))
            if error:
                await manager.send_state(websocket, error)
            else:
                await manager.broadcast()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast()

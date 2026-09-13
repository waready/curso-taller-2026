# Cartas Casino — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/09-cartas-casino) · [Descargar ZIP](/downloads/09-cartas-casino.zip) · [Abrir app.py](/source/09-cartas-casino/app.py) · [Abrir index.html](/source/09-cartas-casino/static/index.html)

Rondas compartidas de apuestas con dos cartas comunes, A y B. Cada jugador recibe
S/ 20.00 al entrar y puede apostar una vez por ronda.

Tienes 8 segundos para elegir una caja y una carta. Al cierre se revelan las
dos cartas para toda la sala: quien aposto por la carta mayor cobra el doble.
Si empatan, se devuelve la apuesta. Los resultados se muestran durante 4 segundos.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en varias pestañas.


## Ejecutar

```powershell
cd codigo\09-cartas-casino
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
```python
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
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cartas Casino</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; color: #f9fafb; background: radial-gradient(circle at 50% 0%, #185f4f, #031c19 62%); }
    main { width: min(900px, 92vw); padding: 1.4rem 0; }
    .top { display: flex; justify-content: space-between; gap: 1rem; align-items: end; margin-bottom: 1rem; }
    h1 { margin: 0; font-size: clamp(2.5rem, 8vw, 5rem); letter-spacing: -.07em; }
    #balance { border-radius: 18px; padding: .8rem 1rem; color: #052e2b; background: #f7d774; font-weight: 950; font-size: 1.2rem; white-space: nowrap; }
    .table { border: 1px solid #4f9e83; border-radius: 28px; padding: 1.5rem; background: #0a3f35cc; box-shadow: 0 28px 90px #0008; }
    .round-bar { display: flex; justify-content: space-between; gap: 1rem; align-items: center; border-radius: 14px; padding: .75rem .9rem; color: #052e2b; background: #c7f9e9; font-weight: 950; }
    #timer { font-variant-numeric: tabular-nums; font-size: 1.25rem; }
    .rules { margin: 1rem 0 0; color: #c7f9e9; line-height: 1.5; text-align: center; }
    .cards { display: grid; grid-template-columns: 1fr auto 1fr; align-items: start; gap: 1rem; margin: 1.4rem 0; }
    .seat { display: grid; justify-items: center; gap: .6rem; color: #c7f9e9; font-weight: 800; }
    .seat.winner { color: #f7d774; }
    .seat.winner .playing-card { box-shadow: 0 0 0 5px #f7d774, 0 12px 24px #001b18aa; }
    .versus { align-self: center; padding-top: 2rem; font-weight: 950; color: #f7d774; }
    .playing-card { display: grid; align-content: space-between; width: 126px; height: 178px; border: 5px solid #f8fafc; border-radius: 14px; padding: .6rem; color: #111827; background: #fff; box-shadow: 0 12px 24px #001b18aa; font-family: Georgia, serif; font-size: 1.45rem; font-weight: 900; }
    .playing-card .middle { place-self: center; font-size: 4rem; }
    .playing-card .bottom { justify-self: end; transform: rotate(180deg); }
    .playing-card.red { color: #dc2626; }
    .playing-card.back { display: grid; place-content: center; color: #f7d774; background: repeating-linear-gradient(45deg, #0b3d68 0 8px, #155b92 8px 16px); font-size: 3rem; }
    .bet-title { margin: .15rem 0 0; color: #c7f9e9; font-size: .85rem; }
    .bet-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .35rem; width: min(260px, 100%); }
    button { border: 1px solid #71bfa5; border-radius: 10px; padding: .65rem .35rem; cursor: pointer; color: #052e2b; background: #f7d774; font: inherit; font-size: .82rem; font-weight: 950; transition: transform .15s, opacity .15s; }
    button:hover:not(:disabled) { transform: translateY(-2px); }
    button:disabled { cursor: not-allowed; opacity: .36; }
    button.selected:disabled { border-color: #fff; color: #052e2b; background: #a7f3d0; opacity: 1; }
    #bet-status { min-height: 1.5rem; margin: 0; color: #f7d774; text-align: center; font-weight: 850; }
    #winners { margin-top: 1.2rem; border-top: 1px solid #4f9e83; padding-top: 1rem; text-align: center; }
    #winners h2 { margin: 0; color: #f7d774; }
    #winner-list { display: grid; gap: .35rem; margin: .7rem 0 0; padding: 0; list-style: none; color: #fff; font-weight: 800; }
    #message { min-height: 1.5rem; margin: 1.1rem 0 0; text-align: center; font-weight: 850; }
    .win { color: #f7d774; } .loss { color: #fca5a5; } .tie { color: #bfdbfe; }
    dialog { border: 1px solid #71bfa5; border-radius: 20px; padding: 1.5rem; color: white; background: #0a3f35; }
    dialog::backdrop { background: #020c0ada; }
    form { display: grid; gap: .8rem; width: min(360px, 78vw); }
    input, form button { border: 1px solid #71bfa5; border-radius: 12px; padding: .9rem; color: white; background: #0b5042; font: inherit; }
    form button { color: #052e2b; background: #f7d774; font-weight: 900; }
    @media (max-width: 600px) { .top { align-items: start; flex-direction: column; } .playing-card { width: 98px; height: 140px; } .cards { gap: .45rem; } .versus { padding-top: 1.5rem; } .bet-grid { grid-template-columns: repeat(2, 1fr); } }
  </style>
</head>
<body>
  <main><div class="top"><div><h1>Cartas</h1><div id="player-name">Casino en vivo</div></div><div id="balance">Saldo: S/ 20.00</div></div><section class="table"><div class="round-bar"><span id="round">Ronda 1 - Apuestas</span><strong id="timer">00:08</strong></div><p class="rules">Todos ven las mismas cartas. Elige una caja debajo de Carta A o Carta B. Si tu carta es la mayor, cobras el doble. Hay 8 segundos para apostar y 4 para resultados.</p><div class="cards"><section class="seat" id="seat-a"><span>Carta A</span><article id="card-a" class="playing-card back">A</article><p class="bet-title">Apostar por A</p><div class="bet-grid"><button data-side="a" data-bet="2.5">S/ 2.50</button><button data-side="a" data-bet="5">S/ 5.00</button><button data-side="a" data-bet="10">S/ 10.00</button><button data-side="a" data-bet="20">S/ 20.00</button><button data-side="a" data-bet="30">S/ 30.00</button><button data-side="a" data-bet="50">S/ 50.00</button></div></section><div class="versus">VS</div><section class="seat" id="seat-b"><span>Carta B</span><article id="card-b" class="playing-card back">B</article><p class="bet-title">Apostar por B</p><div class="bet-grid"><button data-side="b" data-bet="2.5">S/ 2.50</button><button data-side="b" data-bet="5">S/ 5.00</button><button data-side="b" data-bet="10">S/ 10.00</button><button data-side="b" data-bet="20">S/ 20.00</button><button data-side="b" data-bet="30">S/ 30.00</button><button data-side="b" data-bet="50">S/ 50.00</button></div></section></div><p id="bet-status">Esperando tu apuesta.</p><section id="winners" hidden><h2>Ganadores de la ronda</h2><ul id="winner-list"></ul></section><p id="message">Ingresa para recibir S/ 20.00.</p></section></main>
  <dialog id="login" open><form id="form"><h2>Nombre del jugador</h2><input id="name" maxlength="18" required autofocus placeholder="Ej. Jugador 1"><button>Entrar con S/ 20.00</button></form></dialog>
  <script>
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const suits = { hearts: ['&hearts;', 'red'], diamonds: ['&diams;', 'red'], clubs: ['&clubs;', 'black'], spades: ['&spades;', 'black'] };
    let socket, balance = 20, endsAt = 0;
    const money = amount => `S/ ${Number(amount).toFixed(2)}`;
    document.querySelector('#form').addEventListener('submit', event => {
      event.preventDefault(); socket = new WebSocket(`${protocol}://${location.host}/ws`);
      socket.addEventListener('open', () => { socket.send(JSON.stringify({ type: 'join', name: document.querySelector('#name').value })); document.querySelector('#login').close(); });
      socket.addEventListener('message', ({ data }) => render(JSON.parse(data)));
    });
    function card(target, data, label) {
      if (!data) { target.className = 'playing-card back'; target.textContent = label; return; }
      const [symbol, color] = suits[data.suit]; target.className = `playing-card ${color}`;
      target.innerHTML = `<span>${data.rank}${symbol}</span><span class="middle">${symbol}</span><span class="bottom">${data.rank}${symbol}</span>`;
    }
    function render(data) {
      balance = Number(data.balance); endsAt = Number(data.ends_at);
      document.querySelector('#balance').textContent = `Saldo: ${money(balance)}`;
      document.querySelector('#player-name').textContent = `${data.name} - ${data.players} jugador${data.players === 1 ? '' : 'es'}`;
      document.querySelector('#round').textContent = data.phase === 'betting' ? `Ronda ${data.round} - Apuestas (${data.bet_count})` : `Ronda ${data.round} - Resultados`;
      card(document.querySelector('#card-a'), data.phase === 'results' ? data.card_a : null, 'A');
      card(document.querySelector('#card-b'), data.phase === 'results' ? data.card_b : null, 'B');
      document.querySelector('#seat-a').classList.toggle('winner', data.phase === 'results' && data.winning_side === 'a');
      document.querySelector('#seat-b').classList.toggle('winner', data.phase === 'results' && data.winning_side === 'b');
      const hasBet = data.your_bet !== null;
      document.querySelectorAll('[data-bet]').forEach(button => {
        const amount = Number(button.dataset.bet);
        button.disabled = data.phase !== 'betting' || hasBet || balance < amount;
        button.classList.toggle('selected', hasBet && amount === Number(data.your_bet) && button.dataset.side === data.your_choice);
      });
      document.querySelectorAll('.bet-grid, .bet-title').forEach(item => { item.hidden = data.phase !== 'betting'; });
      const status = document.querySelector('#bet-status');
      status.textContent = data.phase === 'betting' ? (hasBet ? `Apuesta registrada: ${money(data.your_bet)} por Carta ${data.your_choice.toUpperCase()}` : 'Elige una caja antes del cierre.') : 'Apuestas cerradas. Se revelan las mismas cartas para todos.';
      const winners = document.querySelector('#winners'); winners.hidden = data.phase !== 'results';
      const noWinners = data.winning_side === 'tie' ? 'Las cartas empataron: se devolvieron las apuestas.' : 'No hubo ganadores en esta ronda.';
      document.querySelector('#winner-list').replaceChildren(...(data.winners.length ? data.winners : [{ name: noWinners, amount: null }]).map(winner => { const item = document.createElement('li'); item.textContent = winner.amount === null ? winner.name : `${winner.name} aposto por ${winner.choice} y cobro ${money(winner.amount)}`; return item; }));
      const message = document.querySelector('#message');
      if (data.error) { message.textContent = data.error; message.className = 'loss'; }
      else if (data.phase === 'results' && data.result === 'win') { message.textContent = `Ganaste ${money(data.payout)} con Carta ${data.your_choice.toUpperCase()}.`; message.className = 'win'; }
      else if (data.phase === 'results' && data.result === 'tie') { message.textContent = 'Las cartas empataron: se devolvio tu apuesta.'; message.className = 'tie'; }
      else if (data.phase === 'results' && data.result === 'loss') { message.textContent = 'Esta vez la otra carta fue mayor.'; message.className = 'loss'; }
      else { message.textContent = data.phase === 'betting' ? 'La ronda esta abierta.' : 'Mira los resultados de la ronda.'; message.className = ''; }
      updateTimer();
    }
    function updateTimer() { const seconds = Math.max(0, Math.ceil(endsAt - Date.now() / 1000)); document.querySelector('#timer').textContent = `00:${String(seconds).padStart(2, '0')}`; }
    setInterval(updateTimer, 150);
    document.querySelectorAll('[data-bet]').forEach(button => button.addEventListener('click', () => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'bet', amount: Number(button.dataset.bet), side: button.dataset.side })); }));
  </script>
</body>
</html>
```
:::

::: details requirements.txt — dependencias
```text
fastapi==0.116.1
uvicorn[standard]==0.35.0
```
:::

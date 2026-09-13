# Subasta Flash — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/08-subasta-flash) · [Descargar ZIP](/downloads/08-subasta-flash.zip) · [Abrir app.py](/source/08-subasta-flash/app.py) · [Abrir index.html](/source/08-subasta-flash/static/index.html)

Todos compiten por un objeto misterioso. El servidor valida la puja y mantiene el precio ganador.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en varias pestañas.


## Ejecutar

```powershell
cd codigo\08-subasta-flash
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
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Subasta Flash</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; color: #fff7ed; background: radial-gradient(circle at 50% 10%, #5b2915, #120907 60%); }
    main { display: grid; grid-template-columns: 1.2fr .8fr; gap: 1.2rem; width: min(980px, 92vw); }
    .card { border: 1px solid #7a452b; border-radius: 24px; padding: 1.5rem; background: #25110bdd; box-shadow: 0 28px 90px #0008; }
    .mystery { display: grid; place-items: center; min-height: 190px; border-radius: 18px; background: linear-gradient(135deg, #f97316, #facc15); font-size: 6rem; }
    h1 { margin: 1rem 0 .2rem; font-size: clamp(2rem, 5vw, 4.3rem); line-height: .95; letter-spacing: -.06em; }
    #price { margin: .8rem 0; color: #fde047; font-size: clamp(3rem, 8vw, 6rem); font-weight: 950; letter-spacing: -.07em; }
    #leader, #timer { color: #fdba74; font-weight: 800; }
    #timer { border-radius: 12px; padding: .65rem; color: #3d1808; background: #fde68a; text-align: center; }
    #reset { width: 100%; margin-top: .6rem; color: #fff7ed; background: #6b2712; }
    form { display: grid; grid-template-columns: 1fr auto; gap: .6rem; margin-top: 1rem; }
    input, button { border: 1px solid #925839; border-radius: 12px; padding: .9rem; color: white; background: #371b11; font: inherit; }
    button { cursor: pointer; color: #241006; background: #fb923c; font-weight: 900; }
    .rule, #result { color: #fed7aa; line-height: 1.45; }
    #error { min-height: 1.4rem; color: #fca5a5; }
    ol { padding-left: 1.4rem; }
    li { margin: .65rem 0; color: #fed7aa; }
    dialog { border: 1px solid #925839; border-radius: 20px; padding: 1.5rem; color: white; background: #29130c; }
    dialog::backdrop { background: #080302dd; }
    dialog form { grid-template-columns: 1fr; width: min(360px, 78vw); }
    @media (max-width: 720px) { main { grid-template-columns: 1fr; padding: 1.2rem 0; } }
  </style>
</head>
<body>
  <main><section class="card"><div class="mystery">&#128230;</div><h1 id="item">Caja misteriosa</h1><div id="timer">Tiempo: 01:00</div><button id="reset" type="button">Reiniciar subasta</button><div id="price">S/ 100.00</div><div id="leader">Lidera: Nadie</div><p class="rule">Regla: tu monto debe ser mayor que el monto actual.</p><form id="bid-form"><input id="amount" type="number" min="100.01" step="0.01" required><button>Pujar</button></form><div id="error"></div><p id="result"></p></section><aside class="card"><h2>Ultimas pujas</h2><p id="connections">Conectando...</p><ol id="history"></ol></aside></main>
  <dialog id="login" open><form id="login-form"><h2>Nombre del postor</h2><input id="name" maxlength="20" required autofocus placeholder="Ej. Equipo 4"><button>Entrar a la subasta</button></form></dialog>
  <script>
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    let socket, currentPrice = 100, endsAt = 0;
    const money = amount => `S/ ${Number(amount).toFixed(2)}`;
    document.querySelector('#login-form').addEventListener('submit', event => {
      event.preventDefault(); socket = new WebSocket(`${protocol}://${location.host}/ws`);
      socket.addEventListener('open', () => { socket.send(JSON.stringify({ type: 'join', name: document.querySelector('#name').value })); document.querySelector('#login').close(); });
      socket.addEventListener('message', ({ data }) => { const event = JSON.parse(data); if (event.type === 'state') render(event); if (event.type === 'error') document.querySelector('#error').textContent = event.message; });
    });
    document.querySelector('#reset').addEventListener('click', () => {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'reset' }));
    });
    function render(event) {
      currentPrice = Number(event.price); endsAt = Number(event.ends_at);
      document.querySelector('#item').textContent = event.item;
      document.querySelector('#price').textContent = money(event.price);
      document.querySelector('#leader').textContent = `Lidera: ${event.leader}`;
      document.querySelector('#connections').textContent = `${event.connections} postor${event.connections === 1 ? '' : 'es'} conectado${event.connections === 1 ? '' : 's'}`;
      const nextBid = (currentPrice + .01).toFixed(2); document.querySelector('#amount').value = nextBid; document.querySelector('#amount').min = nextBid;
      document.querySelector('#history').replaceChildren(...event.history.map(bid => { const item = document.createElement('li'); item.textContent = `${bid.name} ofrecio ${money(bid.amount)}`; return item; }));
      document.querySelector('#result').textContent = event.last_result; document.querySelector('#error').textContent = '';
      updateTimer();
    }
    function updateTimer() {
      const seconds = Math.max(0, Math.ceil(endsAt - Date.now() / 1000));
      const minutes = String(Math.floor(seconds / 60)).padStart(2, '0');
      document.querySelector('#timer').textContent = `Tiempo: ${minutes}:${String(seconds % 60).padStart(2, '0')}`;
    }
    setInterval(updateTimer, 250);
    document.querySelector('#bid-form').addEventListener('submit', event => { event.preventDefault(); const amount = Number(document.querySelector('#amount').value); if (socket?.readyState === WebSocket.OPEN && amount > currentPrice) socket.send(JSON.stringify({ type: 'bid', amount })); });
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

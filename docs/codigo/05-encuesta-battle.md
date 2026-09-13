# Encuesta Battle — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/05-encuesta-battle) · [Descargar ZIP](/downloads/05-encuesta-battle.zip) · [Abrir app.py](/source/05-encuesta-battle/app.py) · [Abrir index.html](/source/05-encuesta-battle/static/index.html)

Votación A/B/C/D con resultados animados en tiempo real. Cada conexión tiene un voto y puede cambiarlo.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en varias pestañas.


## Ejecutar

```powershell
cd codigo\05-encuesta-battle
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
```python
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
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Encuesta Battle</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; color: #f5f8ff; background: radial-gradient(circle at top, #38266b, #090c1a 58%); }
    main { width: min(900px, 92vw); padding: 2rem 0; }
    header { text-align: center; }
    h1 { margin: 0; font-size: clamp(2.5rem, 8vw, 6rem); line-height: .95; letter-spacing: -.07em; }
    #meta { color: #c7b9ff; font-weight: 700; }
    #options { display: grid; gap: 1rem; margin-top: 2.2rem; }
    .option { position: relative; overflow: hidden; min-height: 72px; border: 1px solid #594b88; border-radius: 18px; padding: 0; cursor: pointer; color: white; background: #17142b; text-align: left; }
    .bar { position: absolute; inset: 0 auto 0 0; width: 0; background: linear-gradient(90deg, #6538d6, #18cfc2); transition: width 350ms ease; opacity: .72; }
    .label { position: relative; display: flex; justify-content: space-between; gap: 1rem; padding: 1.35rem 1.5rem; font-size: 1.12rem; font-weight: 800; }
    .option.selected { outline: 3px solid #75f0e7; }
    .option:hover { transform: translateY(-2px); }
  </style>
</head>
<body>
  <main>
    <header><h1 id="question">Cargando pregunta…</h1><p id="meta">Conectando…</p></header>
    <section id="options" aria-live="polite"></section>
  </main>
  <script>
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${location.host}/ws`);
    const options = document.querySelector('#options');
    let selected = null;

    function render(event) {
      document.querySelector('#question').textContent = event.question;
      document.querySelector('#meta').textContent = `${event.total} votos · ${event.connections} conexiones`;
      options.replaceChildren(...Object.entries(event.options).map(([key, label]) => {
        const votes = event.counts[key];
        const percent = event.total ? Math.round(votes * 100 / event.total) : 0;
        const button = document.createElement('button');
        button.className = `option ${selected === key ? 'selected' : ''}`;
        button.innerHTML = `<span class="bar" style="width:${percent}%"></span><span class="label"><span>${label}</span><span>${votes} · ${percent}%</span></span>`;
        button.addEventListener('click', () => {
          selected = key;
          socket.send(JSON.stringify({ type: 'vote', option: key }));
        });
        return button;
      }));
    }

    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data);
      if (event.type === 'state') render(event);
    });
    socket.addEventListener('close', () => document.querySelector('#meta').textContent = 'Desconectado');
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

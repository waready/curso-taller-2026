# Reacciones en vivo — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/04-reacciones-en-vivo) · [Descargar ZIP](/downloads/04-reacciones-en-vivo.zip) · [Abrir app.py](/source/04-reacciones-en-vivo/app.py) · [Abrir index.html](/source/04-reacciones-en-vivo/static/index.html)

Muro de emojis y contadores sincronizados para una demostración con audiencia.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en varias pestañas.

Reto: agrega una encuesta, límite de velocidad o una reacción dominante.


## Ejecutar

```powershell
cd codigo\04-reacciones-en-vivo
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
```python
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
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reacciones en vivo</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; overflow: hidden; color: #f4f8ff; background: radial-gradient(circle at 50% 30%, #243568, #09111f 55%); }
    main { position: relative; z-index: 1; width: min(900px, 92vw); margin: auto; padding-top: 8vh; text-align: center; }
    h1 { margin: 0; font-size: clamp(2.8rem, 9vw, 7rem); line-height: .9; letter-spacing: -.07em; }
    #presence { margin: 1rem; color: #70e7df; font-weight: 800; }
    .buttons { display: grid; grid-template-columns: repeat(4, 1fr); gap: .8rem; margin: 3rem auto 1.3rem; }
    .reaction { border: 1px solid rgb(255 255 255 / 14%); border-radius: 22px; padding: 1.1rem .5rem; cursor: pointer; color: white; background: rgb(18 35 64 / 82%); font-size: clamp(2.2rem, 6vw, 4rem); transition: transform 100ms ease, background 100ms ease; }
    .reaction:hover { transform: translateY(-5px); background: #20385f; }
    .reaction span { display: block; margin-top: .25rem; color: #aabbd0; font-size: 1rem; font-weight: 800; }
    #reset { border: 0; padding: .6rem 1rem; cursor: pointer; color: #93a6be; background: transparent; }
    .float { position: fixed; bottom: -70px; z-index: 0; pointer-events: none; animation: rise 2.2s ease-out forwards; font-size: clamp(2.5rem, 7vw, 5rem); }
    @keyframes rise { to { transform: translateY(-115vh) rotate(18deg); opacity: 0; } }
    @media (max-width: 620px) { .buttons { grid-template-columns: repeat(2, 1fr); margin-top: 2rem; } }
    @media (prefers-reduced-motion: reduce) { .float { animation-duration: .3s; } }
  </style>
</head>
<body>
  <main>
    <h1>¿Cómo va la clase?</h1>
    <div id="presence">Conectando…</div>
    <section class="buttons" aria-label="Reacciones"></section>
    <button id="reset">Reiniciar conteos</button>
  </main>
  <script>
    const emojis = ['🔥','👏','🤯','❤️'];
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${location.host}/ws`);
    const buttons = document.querySelector('.buttons');

    buttons.replaceChildren(...emojis.map(emoji => {
      const button = document.createElement('button');
      button.className = 'reaction';
      button.dataset.emoji = emoji;
      button.append(document.createTextNode(emoji));
      const count = document.createElement('span');
      count.textContent = '0';
      button.append(count);
      button.addEventListener('click', () => {
        if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'reaction', emoji }));
      });
      return button;
    }));

    function updateCounts(counts) {
      document.querySelectorAll('.reaction').forEach(button => {
        button.querySelector('span').textContent = counts[button.dataset.emoji] ?? 0;
      });
    }

    function floatEmoji(emoji) {
      const item = document.createElement('div');
      item.className = 'float';
      item.textContent = emoji;
      item.style.left = `${5 + Math.random() * 90}%`;
      item.style.animationDuration = `${1.6 + Math.random() * 1.4}s`;
      document.body.append(item);
      item.addEventListener('animationend', () => item.remove());
    }

    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data);
      if (event.type === 'state') updateCounts(event.counts);
      if (event.type === 'reaction') { updateCounts(event.counts); floatEmoji(event.emoji); }
      if (event.type === 'presence') document.querySelector('#presence').textContent = `${event.count} participante${event.count === 1 ? '' : 's'} conectado${event.count === 1 ? '' : 's'}`;
    });
    socket.addEventListener('close', () => document.querySelector('#presence').textContent = 'Desconectado');
    document.querySelector('#reset').addEventListener('click', () => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'reset' }));
    });
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

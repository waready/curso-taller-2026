# WebSocket Base — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/01-websocket-base) · [Descargar ZIP](/downloads/01-websocket-base.zip) · [Abrir app.py](/source/01-websocket-base/app.py) · [Abrir index.html](/source/01-websocket-base/static/index.html)

Práctica común: mensajes y cantidad de conexiones en una sola instancia de FastAPI.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en dos pestañas.

Reto: agrega el nombre del grupo, impide mensajes vacíos y comprueba que cerrar una pestaña no detenga las demás.


## Ejecutar

```powershell
cd codigo\01-websocket-base
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


app = FastAPI(title="WebSocket Base")
BASE_DIR = Path(__file__).parent


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event)
            except RuntimeError:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "connections": len(manager.active_connections)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await manager.broadcast(
        {"type": "presence", "count": len(manager.active_connections)}
    )
    try:
        while True:
            data = await websocket.receive_json()
            text = str(data.get("text", "")).strip()[:120]
            user = str(data.get("user", "Anónimo")).strip()[:24] or "Anónimo"
            if text:
                await manager.broadcast(
                    {"type": "message", "user": user, "text": text}
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(
            {"type": "presence", "count": len(manager.active_connections)}
        )
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WebSocket Base</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; color: #e8f2ff; background: #07111f; }
    main { width: min(680px, 92vw); }
    header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
    h1 { margin: 0; font-size: clamp(2rem, 7vw, 4.2rem); letter-spacing: -.06em; }
    #status { color: #77eadf; font-weight: 700; }
    form { display: grid; grid-template-columns: 150px 1fr auto; gap: .6rem; margin: 1.5rem 0; }
    input, button { border: 1px solid #2a4666; border-radius: 12px; padding: .85rem; font: inherit; }
    input { min-width: 0; color: #fff; background: #0c1c30; }
    button { cursor: pointer; color: #031514; background: #53e0d6; font-weight: 800; }
    #messages { min-height: 260px; max-height: 50vh; overflow: auto; border: 1px solid #203a59; border-radius: 18px; padding: 1rem; background: #0a1728; }
    .message { margin: .55rem 0; padding: .7rem .85rem; border-radius: 10px; background: #10243b; }
    .message strong { color: #77eadf; }
    @media (max-width: 620px) { form { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header><h1>Muro en vivo</h1><span id="status">Conectando…</span></header>
    <form id="form">
      <input id="user" value="grupo-1" maxlength="24" aria-label="Nombre">
      <input id="text" placeholder="Escribe un mensaje" maxlength="120" autocomplete="off" required>
      <button>Enviar</button>
    </form>
    <section id="messages" aria-live="polite"></section>
  </main>
  <script>
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${location.host}/ws`);
    const status = document.querySelector('#status');
    const messages = document.querySelector('#messages');

    socket.addEventListener('open', () => status.textContent = 'Conectado');
    socket.addEventListener('close', () => status.textContent = 'Desconectado');
    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data);
      if (event.type === 'presence') {
        status.textContent = `${event.count} conectado${event.count === 1 ? '' : 's'}`;
      }
      if (event.type === 'message') {
        const item = document.createElement('div');
        item.className = 'message';
        const author = document.createElement('strong');
        author.textContent = `${event.user}: `;
        item.append(author, document.createTextNode(event.text));
        messages.append(item);
        messages.scrollTop = messages.scrollHeight;
      }
    });

    document.querySelector('#form').addEventListener('submit', (event) => {
      event.preventDefault();
      const text = document.querySelector('#text');
      const user = document.querySelector('#user');
      if (socket.readyState === WebSocket.OPEN && text.value.trim()) {
        socket.send(JSON.stringify({ type: 'message', user: user.value, text: text.value }));
        text.value = '';
        text.focus();
      }
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

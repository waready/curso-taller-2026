# Mini-WPlace colaborativo — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/03-wplace-colaborativo) · [Descargar ZIP](/downloads/03-wplace-colaborativo.zip) · [Abrir app.py](/source/03-wplace-colaborativo/app.py) · [Abrir index.html](/source/03-wplace-colaborativo/static/index.html)

Tablero 20 × 20 sincronizado por WebSocket. El estado vive en la memoria de una instancia de FastAPI.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en dos pestañas.

Reto: agrega enfriamiento por usuario, historial o descarga del tablero.


## Ejecutar

```powershell
cd codigo\03-wplace-colaborativo
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
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WPlace colaborativo</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; color: #edf5ff; background: radial-gradient(circle at 50% 0%, #132b47, #07111f 45%); }
    main { width: min(920px, 94vw); margin: auto; padding: 2rem 0; text-align: center; }
    h1 { margin: 0; font-size: clamp(2.2rem, 7vw, 4.8rem); letter-spacing: -.065em; }
    header p { color: #9bb0c7; }
    #status { color: #5ce9df; font-weight: 800; }
    #reset { border: 1px solid #52718f; border-radius: 10px; padding: .55rem .8rem; cursor: pointer; color: #eaf7ff; background: #1b324e; font: inherit; font-weight: 800; }
    #palette { display: flex; justify-content: center; flex-wrap: wrap; gap: .55rem; margin: 1.25rem 0; }
    .color { width: 38px; height: 38px; border: 3px solid transparent; border-radius: 12px; cursor: pointer; box-shadow: inset 0 0 0 1px rgb(255 255 255 / 18%); }
    .color.selected { border-color: white; transform: scale(1.12); }
    #board { display: grid; width: min(76vh, 90vw); aspect-ratio: 1; margin: 0 auto; border: 8px solid #1b324e; border-radius: 12px; overflow: hidden; background: #111827; box-shadow: 0 24px 80px rgb(0 0 0 / 35%); touch-action: none; }
    .pixel { border: 0; padding: 0; cursor: crosshair; }
    #toast { min-height: 1.4rem; margin-top: .8rem; color: #fca5a5; }
  </style>
</head>
<body>
  <main>
    <header><h1>WPlace mínimo</h1><p><span id="status">Conectando…</span> · pinta algo con tu grupo</p></header>
    <button id="reset" type="button">Limpiar tablero</button>
    <div id="palette" aria-label="Paleta de colores"></div>
    <div id="board" aria-label="Tablero colaborativo"></div>
    <div id="toast" aria-live="polite"></div>
  </main>
  <script>
    const colors = ['#ef4444','#f97316','#facc15','#22c55e','#15d1c5','#3b82f6','#a855f7','#ec4899','#f8fafc','#111827'];
    let selected = colors[4];
    let size = 20;
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${location.host}/ws`);
    const board = document.querySelector('#board');
    const palette = document.querySelector('#palette');
    document.querySelector('#reset').addEventListener('click', () => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'reset' }));
    });

    function makeBoard(nextSize) {
      size = nextSize;
      board.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
      board.replaceChildren(...Array.from({ length: size * size }, (_, index) => {
        const pixel = document.createElement('button');
        pixel.className = 'pixel';
        pixel.dataset.x = index % size;
        pixel.dataset.y = Math.floor(index / size);
        pixel.setAttribute('aria-label', `Píxel ${pixel.dataset.x}, ${pixel.dataset.y}`);
        pixel.addEventListener('pointerdown', () => paint(Number(pixel.dataset.x), Number(pixel.dataset.y)));
        return pixel;
      }));
    }

    function paint(x, y) {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'paint', x, y, color: selected }));
    }

    palette.replaceChildren(...colors.map((color, index) => {
      const button = document.createElement('button');
      button.className = `color ${index === 4 ? 'selected' : ''}`;
      button.style.background = color;
      button.setAttribute('aria-label', `Elegir ${color}`);
      button.addEventListener('click', () => {
        selected = color;
        document.querySelectorAll('.color').forEach(item => item.classList.remove('selected'));
        button.classList.add('selected');
      });
      return button;
    }));

    makeBoard(size);
    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data);
      if (event.type === 'board') {
        if (event.size !== size) makeBoard(event.size);
        event.pixels.forEach((color, index) => board.children[index].style.background = color);
      }
      if (event.type === 'paint') board.children[event.y * size + event.x].style.background = event.color;
      if (event.type === 'presence') document.querySelector('#status').textContent = `${event.count} artista${event.count === 1 ? '' : 's'} en línea`;
      if (event.type === 'error') document.querySelector('#toast').textContent = event.message;
    });
    socket.addEventListener('close', () => document.querySelector('#status').textContent = 'Desconectado');
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

# Cursor Party — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/06-cursor-party) · [Descargar ZIP](/downloads/06-cursor-party.zip) · [Abrir app.py](/source/06-cursor-party/app.py) · [Abrir index.html](/source/06-cursor-party/static/index.html)

Todos ven los cursores de los demás moverse en tiempo real y pueden dibujar
en una pizarra compartida. Cada sala mantiene sus propios cursores y líneas;
quien crea la sala puede limpiarla y cada persona puede deshacer su última
línea. Funciona con mouse, pantalla táctil y lápiz digital.

Ejecuta `uvicorn app:app --reload` y abre `http://127.0.0.1:8000` en varias pestañas o computadoras.


## Ejecutar

```powershell
cd codigo\06-cursor-party
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


app = FastAPI(title="Cursor Party")
BASE_DIR = Path(__file__).parent
COLORS = ("#22d3ee", "#a78bfa", "#fb7185", "#facc15", "#4ade80", "#fb923c")
MAX_LINES = 500


def clean_label(value: object, fallback: str, limit: int) -> str:
    label = " ".join(str(value or "").split())[:limit]
    return label or fallback


def percentage(value: object, fallback: float = 50) -> float:
    try:
        return max(0, min(100, float(value)))
    except (TypeError, ValueError):
        return fallback


class PartyRoom:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}
        self.lines: list[dict] = []
        self.owner_id: str | None = None
        self.line_revision = 0


class CursorManager:
    def __init__(self) -> None:
        self.rooms: dict[str, PartyRoom] = {}
        self.room_by_socket: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def join(self, websocket: WebSocket, name: object, room_name: object) -> tuple[dict, str]:
        room_key = clean_label(room_name, "Sala general", 24)
        room = self.rooms.setdefault(room_key, PartyRoom())
        cursor_id = uuid4().hex[:8]
        cursor = {
            "id": cursor_id,
            "name": clean_label(name, "Anonimo", 18),
            "color": COLORS[len(room.clients) % len(COLORS)],
            "x": 50,
            "y": 50,
        }
        room.clients[websocket] = cursor
        self.room_by_socket[websocket] = room_key
        if room.owner_id is None:
            room.owner_id = cursor_id
        return cursor, room_key

    def room_for(self, websocket: WebSocket) -> tuple[str, PartyRoom] | None:
        room_key = self.room_by_socket.get(websocket)
        if not room_key:
            return None
        room = self.rooms.get(room_key)
        return (room_key, room) if room else None

    def disconnect(self, websocket: WebSocket) -> str | None:
        room_key = self.room_by_socket.pop(websocket, None)
        if not room_key:
            return None

        room = self.rooms.get(room_key)
        if not room:
            return None
        cursor = room.clients.pop(websocket, None)
        if cursor and room.owner_id == cursor["id"]:
            next_cursor = next(iter(room.clients.values()), None)
            room.owner_id = next_cursor["id"] if next_cursor else None
        if not room.clients:
            self.rooms.pop(room_key, None)
            return None
        return room_key

    async def send_error(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_json({"type": "error", "message": message})

    async def broadcast(self, room_key: str) -> None:
        room = self.rooms.get(room_key)
        if not room:
            return
        event = {
            "type": "state",
            "room": room_key,
            "owner_id": room.owner_id,
            "cursors": list(room.clients.values()),
            "lines": room.lines,
            "line_revision": room.line_revision,
        }
        disconnected: list[WebSocket] = []
        for client in list(room.clients):
            try:
                await client.send_json(event)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(client)
        for client in disconnected:
            self.disconnect(client)


manager = CursorManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.websocket("/ws")
async def cursor_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        if not isinstance(first, dict) or first.get("type") != "join":
            await manager.send_error(websocket, "Envia primero tu nombre y sala.")
            return

        cursor, room_key = await manager.join(websocket, first.get("name"), first.get("room"))
        await websocket.send_json(
            {
                "type": "welcome",
                "id": cursor["id"],
                "color": cursor["color"],
                "room": room_key,
                "is_owner": cursor["id"] == manager.rooms[room_key].owner_id,
            }
        )
        await manager.broadcast(room_key)

        while True:
            event = await websocket.receive_json()
            if not isinstance(event, dict):
                await manager.send_error(websocket, "El evento debe ser un objeto JSON.")
                continue

            active_room = manager.room_for(websocket)
            if not active_room:
                return
            room_key, room = active_room
            own_cursor = room.clients[websocket]
            event_type = event.get("type")

            if event_type == "move":
                own_cursor["x"] = percentage(event.get("x"))
                own_cursor["y"] = percentage(event.get("y"))
                await manager.broadcast(room_key)
            elif event_type == "draw":
                line = {
                    "x1": percentage(event.get("x1"), 0),
                    "y1": percentage(event.get("y1"), 0),
                    "x2": percentage(event.get("x2"), 0),
                    "y2": percentage(event.get("y2"), 0),
                    "width": max(0.2, min(1.6, percentage(event.get("width"), 0.45))),
                    "color": own_cursor["color"],
                    "author_id": own_cursor["id"],
                }
                room.lines.append(line)
                room.lines = room.lines[-MAX_LINES:]
                room.line_revision += 1
                await manager.broadcast(room_key)
            elif event_type == "undo":
                for index in range(len(room.lines) - 1, -1, -1):
                    if room.lines[index]["author_id"] == own_cursor["id"]:
                        room.lines.pop(index)
                        room.line_revision += 1
                        await manager.broadcast(room_key)
                        break
            elif event_type == "reset":
                if room.owner_id != own_cursor["id"]:
                    await manager.send_error(websocket, "Solo quien creo la sala puede limpiar la pizarra.")
                    continue
                room.lines.clear()
                room.line_revision += 1
                await manager.broadcast(room_key)
            else:
                await manager.send_error(websocket, "Evento no reconocido.")
    except WebSocketDisconnect:
        pass
    finally:
        room_key = manager.disconnect(websocket)
        if room_key:
            await manager.broadcast(room_key)
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cursor Party</title>
  <style>
    :root { --ink:#10182d; --cyan:#36d9dc; --coral:#ff8c7b; --line:#ffffff42; font-family:"Trebuchet MS","Aptos Display",sans-serif; color:var(--ink); background:var(--ink); }
    * { box-sizing:border-box; }
    body { min-height:100vh; margin:0; overflow:hidden; color:#f8fbff; background:radial-gradient(circle at 12% 12%,#344b7b 0,transparent 31rem),radial-gradient(circle at 85% 88%,#5b3471 0,transparent 32rem),var(--ink); }
    button,input { font:inherit; }
    button { cursor:pointer; }
    #stage { position:fixed; inset:0; overflow:hidden; touch-action:none; background-image:linear-gradient(#ffffff0d 1px,transparent 1px),linear-gradient(90deg,#ffffff0d 1px,transparent 1px); background-size:52px 52px; }
    #stage::before { content:""; position:absolute; inset:0; pointer-events:none; background:radial-gradient(circle at 50% 50%,transparent 0 20%,#080d1f55 85%); }
    #drawing,#cursors { position:absolute; inset:0; width:100%; height:100%; }
    #drawing { pointer-events:none; filter:drop-shadow(0 5px 5px #02061670); }
    .topbar { position:fixed; z-index:3; top:clamp(16px,3vw,34px); left:clamp(16px,3vw,42px); right:clamp(16px,3vw,42px); display:flex; align-items:flex-start; justify-content:space-between; gap:18px; pointer-events:none; }
    .brand { max-width:430px; text-shadow:0 3px 16px #050814a0; }
    .eyebrow { display:block; margin-bottom:7px; color:var(--cyan); font-size:.7rem; font-weight:950; letter-spacing:.16em; text-transform:uppercase; }
    h1 { margin:0; font-family:Georgia,"Palatino Linotype",serif; font-size:clamp(2.3rem,6vw,5.4rem); letter-spacing:-.075em; line-height:.84; }
    .brand p { max-width:350px; margin:13px 0 0; color:#c4d0e8; font-size:.88rem; line-height:1.45; }
    .room-card { display:grid; gap:7px; min-width:190px; border:1px solid var(--line); border-radius:18px; padding:12px 15px; color:#eaf2ff; background:#10182dbd; box-shadow:0 20px 50px #05081444; backdrop-filter:blur(12px); }
    .room-card small { color:#9eb2d3; font-size:.68rem; font-weight:850; letter-spacing:.12em; text-transform:uppercase; }
    .room-card strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .connection { display:flex; align-items:center; gap:6px; color:#a5b8d7; font-size:.76rem; font-weight:800; }
    .connection::before { content:""; width:8px; height:8px; border-radius:50%; background:#94a3b8; }
    .connection[data-state="online"]::before { background:#64e6af; box-shadow:0 0 0 4px #64e6af25; }
    .connection[data-state="error"]::before { background:var(--coral); box-shadow:0 0 0 4px #ff8c7b25; }
    .control-panel { position:fixed; z-index:4; right:clamp(16px,3vw,42px); bottom:clamp(16px,3vw,34px); display:grid; gap:9px; width:min(294px,calc(100vw - 32px)); border:1px solid var(--line); border-radius:22px; padding:12px; background:#10182dde; box-shadow:0 20px 55px #05081466; backdrop-filter:blur(16px); }
    .tool-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    button { border:1px solid #ffffff25; border-radius:13px; padding:.74rem .78rem; color:#f7fbff; background:#ffffff11; font-size:.79rem; font-weight:900; transition:transform .18s ease,background .18s ease,border-color .18s ease; }
    button:hover:not(:disabled) { transform:translateY(-2px); border-color:#ffffff60; background:#ffffff21; }
    button:disabled { cursor:not-allowed; opacity:.42; }
    #draw-mode.active { color:#071721; border-color:var(--cyan); background:var(--cyan); box-shadow:0 7px 22px #36d9dc44; }
    #clear-lines { color:#ffe7e2; background:#6f2735b0; }
    #undo-line { color:#e8e3ff; background:#413071b0; }
    .brush { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:10px; padding:7px 9px; color:#bed0eb; font-size:.75rem; font-weight:850; }
    input[type="range"] { accent-color:var(--cyan); }
    .brush output { min-width:33px; color:var(--cyan); font-variant-numeric:tabular-nums; text-align:right; }
    .notice { min-height:18px; padding:0 4px; color:#a9bddb; font-size:.71rem; line-height:1.3; }
    .notice[data-tone="error"] { color:#ffb5a9; }
    .cursor { position:absolute; z-index:1; transform:translate(-3px,-3px); pointer-events:none; transition:left 55ms linear,top 55ms linear; }
    .cursor::before { content:""; display:block; width:0; height:0; border-top:27px solid var(--color); border-right:17px solid transparent; filter:drop-shadow(0 5px 5px #0009); }
    .cursor.own::before { border-top-width:31px; border-right-width:19px; }
    .cursor span { display:block; margin:-4px 0 0 13px; border:1px solid #ffffff66; border-radius:999px; padding:.3rem .6rem; color:#07131d; background:var(--color); box-shadow:0 5px 14px #02061655; font-size:.76rem; font-weight:950; white-space:nowrap; }
    .cursor.own span { outline:3px solid #ffffff35; }
    dialog { border:1px solid #ffffff32; border-radius:24px; padding:0; color:#f8fbff; background:#111a31; box-shadow:0 28px 90px #01030abc; }
    dialog::backdrop { background:#050814c9; backdrop-filter:blur(7px); }
    form { display:grid; gap:14px; width:min(405px,84vw); padding:25px; }
    form h2 { margin:0; font-family:Georgia,"Palatino Linotype",serif; font-size:2.2rem; letter-spacing:-.055em; }
    form p { margin:-4px 0 4px; color:#b7c5de; font-size:.86rem; line-height:1.45; }
    label { display:grid; gap:6px; color:#bdcce5; font-size:.73rem; font-weight:900; letter-spacing:.05em; text-transform:uppercase; }
    input[type="text"] { width:100%; border:1px solid #ffffff2e; border-radius:13px; padding:.85rem .9rem; color:#f8fbff; background:#ffffff0d; outline:none; }
    input[type="text"]:focus { border-color:var(--cyan); box-shadow:0 0 0 4px #36d9dc24; }
    form button { color:#071721; border-color:var(--cyan); background:var(--cyan); }
    @media (max-width:680px) { .topbar { align-items:flex-start; } .brand p { display:none; } .room-card { min-width:0; max-width:43vw; } h1 { font-size:clamp(2.2rem,12vw,4rem); } .control-panel { bottom:16px; } }
  </style>
</head>
<body>
  <main id="stage">
    <svg id="drawing" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"></svg>
    <div id="cursors" aria-label="Cursores conectados"></div>
  </main>
  <header class="topbar">
    <div class="brand"><span class="eyebrow">WebSocket canvas social</span><h1>Cursor Party</h1><p>Mueve tu cursor, dibuja en grupo y comparte la misma pizarra en tiempo real.</p></div>
    <section class="room-card" aria-label="Estado de la sala"><small>Sala activa</small><strong id="room-name">Conectando...</strong><span id="connection" class="connection" data-state="waiting">Esperando ingreso</span></section>
  </header>
  <aside class="control-panel" aria-label="Herramientas de pizarra">
    <div class="tool-row"><button id="draw-mode" type="button">Activar lapiz</button><button id="undo-line" type="button">Deshacer mi linea</button></div>
    <div class="tool-row"><button id="clear-lines" type="button" disabled>Limpiar sala</button><button id="leave-room" type="button">Cambiar sala</button></div>
    <label class="brush" for="brush-size">Grosor<input id="brush-size" type="range" min="0.2" max="1.6" value="0.45" step="0.05"><output id="brush-output">0.45</output></label>
    <div id="notice" class="notice" aria-live="polite">Ingresa a una sala para empezar.</div>
  </aside>
  <dialog id="login" open>
    <form id="form">
      <span class="eyebrow">Tu espacio compartido</span><h2>Entra a la pizarra.</h2><p>Las personas con el mismo nombre de sala se veran y dibujaran juntas.</p>
      <label>Tu nombre<input id="name" type="text" maxlength="18" required autofocus placeholder="Ej. Equipo Puno"></label>
      <label>Nombre de sala<input id="room" type="text" maxlength="24" required value="Sala general" placeholder="Ej. Grupo A"></label>
      <button type="submit">Entrar a la sala</button>
    </form>
  </dialog>
  <script>
    const stage = document.querySelector('#stage');
    const drawing = document.querySelector('#drawing');
    const cursorLayer = document.querySelector('#cursors');
    const drawButton = document.querySelector('#draw-mode');
    const undoButton = document.querySelector('#undo-line');
    const clearLinesButton = document.querySelector('#clear-lines');
    const leaveRoomButton = document.querySelector('#leave-room');
    const brushSize = document.querySelector('#brush-size');
    const brushOutput = document.querySelector('#brush-output');
    const notice = document.querySelector('#notice');
    const roomNameElement = document.querySelector('#room-name');
    const connection = document.querySelector('#connection');
    const login = document.querySelector('#login');
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const cursorNodes = new Map();
    let socket, ownId, ownColor = '#36d9dc', currentRoom = 'Sala general';
    let drawingMode = false, lastPoint = null, lastMove = 0, lastDraw = 0;
    let lastLineRevision = -1, joinedData = null, reconnectTimer = null, isLeaving = false;

    function setStatus(text, state, tone) {
      connection.textContent = text;
      connection.dataset.state = state || 'waiting';
      notice.textContent = text;
      notice.dataset.tone = tone || '';
    }
    function setRoom(name) {
      currentRoom = name || currentRoom;
      roomNameElement.textContent = currentRoom;
    }
    function send(event) {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(event));
    }
    function connect() {
      if (!joinedData) return;
      clearTimeout(reconnectTimer);
      setStatus('Conectando a la sala...', 'waiting');
      const nextSocket = new WebSocket(protocol + '://' + location.host + '/ws');
      socket = nextSocket;
      nextSocket.addEventListener('open', function() {
        nextSocket.send(JSON.stringify({ type:'join', name:joinedData.name, room:joinedData.room }));
      });
      nextSocket.addEventListener('message', function(message) {
        const event = JSON.parse(message.data);
        if (event.type === 'welcome') {
          ownId = event.id;
          ownColor = event.color;
          setRoom(event.room);
          login.close();
          setStatus('Conectado en ' + event.room, 'online');
        } else if (event.type === 'state') {
          render(event);
        } else if (event.type === 'error') {
          setStatus(event.message || 'La sala envio un error.', 'error', 'error');
        }
      });
      nextSocket.addEventListener('close', function() {
        if (socket !== nextSocket || isLeaving || !joinedData) return;
        setStatus('Conexion perdida. Reconectando...', 'error', 'error');
        reconnectTimer = setTimeout(connect, 1400);
      });
      nextSocket.addEventListener('error', function() {
        setStatus('No se pudo conectar. Intentando de nuevo...', 'error', 'error');
      });
    }
    function createLine(line) {
      const part = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      part.setAttribute('x1', line.x1);
      part.setAttribute('y1', line.y1);
      part.setAttribute('x2', line.x2);
      part.setAttribute('y2', line.y2);
      part.setAttribute('stroke', line.color);
      part.setAttribute('stroke-width', line.width || '0.45');
      part.setAttribute('stroke-linecap', 'round');
      return part;
    }
    function renderLines(lines, revision) {
      if (revision === lastLineRevision) return;
      drawing.replaceChildren(...lines.map(createLine));
      lastLineRevision = revision;
    }
    function renderCursors(cursors) {
      const visible = new Set();
      cursors.forEach(function(item) {
        visible.add(item.id);
        let cursor = cursorNodes.get(item.id);
        if (!cursor) {
          cursor = document.createElement('div');
          cursor.className = 'cursor';
          const label = document.createElement('span');
          cursor.append(label);
          cursorLayer.append(cursor);
          cursorNodes.set(item.id, cursor);
        }
        cursor.classList.toggle('own', item.id === ownId);
        cursor.style.left = item.x + '%';
        cursor.style.top = item.y + '%';
        cursor.style.setProperty('--color', item.color);
        cursor.querySelector('span').textContent = item.id === ownId ? item.name + ' (tu)' : item.name;
      });
      cursorNodes.forEach(function(cursor, id) {
        if (!visible.has(id)) {
          cursor.remove();
          cursorNodes.delete(id);
        }
      });
    }
    function render(state) {
      setRoom(state.room);
      renderLines(state.lines, state.line_revision);
      renderCursors(state.cursors);
      const total = state.cursors.length;
      const isOwner = state.owner_id === ownId;
      clearLinesButton.disabled = !isOwner;
      clearLinesButton.title = isOwner ? 'Limpiar todas las lineas de la sala' : 'Solo quien creo la sala puede limpiar';
      if (connection.dataset.state !== 'error') setStatus(total + ' persona' + (total === 1 ? '' : 's') + ' conectada' + (total === 1 ? '' : 's'), 'online');
    }
    function pointFrom(event) {
      const rect = stage.getBoundingClientRect();
      return {
        x: Math.max(0, Math.min(100, (event.clientX - rect.left) * 100 / rect.width)),
        y: Math.max(0, Math.min(100, (event.clientY - rect.top) * 100 / rect.height))
      };
    }
    function sendMove(point) {
      if (Date.now() - lastMove < 42) return;
      lastMove = Date.now();
      send({ type:'move', x:point.x, y:point.y });
    }
    function sendLine(from, to) {
      if (Date.now() - lastDraw < 20) return;
      lastDraw = Date.now();
      send({ type:'draw', x1:from.x, y1:from.y, x2:to.x, y2:to.y, width:Number(brushSize.value), color:ownColor });
    }
    document.querySelector('#form').addEventListener('submit', function(event) {
      event.preventDefault();
      joinedData = { name:document.querySelector('#name').value.trim(), room:document.querySelector('#room').value.trim() };
      isLeaving = false;
      lastLineRevision = -1;
      connect();
    });
    drawButton.addEventListener('click', function() {
      drawingMode = !drawingMode;
      drawButton.classList.toggle('active', drawingMode);
      drawButton.textContent = drawingMode ? 'Lapiz activo' : 'Activar lapiz';
      setStatus(drawingMode ? 'Modo dibujo activo' : 'Modo cursor activo', 'online');
    });
    undoButton.addEventListener('click', function() { send({ type:'undo' }); });
    clearLinesButton.addEventListener('click', function() {
      if (confirm('Se borraran las lineas de toda la sala. Continuar?')) send({ type:'reset' });
    });
    leaveRoomButton.addEventListener('click', function() {
      isLeaving = true;
      clearTimeout(reconnectTimer);
      if (socket) socket.close();
      joinedData = null;
      ownId = undefined;
      lastLineRevision = -1;
      drawing.replaceChildren();
      cursorLayer.replaceChildren();
      cursorNodes.clear();
      clearLinesButton.disabled = true;
      login.showModal();
      setStatus('Elige otra sala para continuar.', 'waiting');
    });
    brushSize.addEventListener('input', function() { brushOutput.textContent = Number(brushSize.value).toFixed(2); });
    stage.addEventListener('pointerdown', function(event) {
      const point = pointFrom(event);
      sendMove(point);
      if (drawingMode) {
        lastPoint = point;
        stage.setPointerCapture(event.pointerId);
        event.preventDefault();
      }
    });
    stage.addEventListener('pointermove', function(event) {
      const point = pointFrom(event);
      sendMove(point);
      if (drawingMode && lastPoint) {
        sendLine(lastPoint, point);
        lastPoint = point;
      }
    });
    stage.addEventListener('pointerup', function() { lastPoint = null; });
    stage.addEventListener('pointercancel', function() { lastPoint = null; });
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

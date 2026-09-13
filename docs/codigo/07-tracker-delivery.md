# Tracker Delivery Puno — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/07-tracker-delivery) · [Descargar ZIP](/downloads/07-tracker-delivery.zip) · [Abrir app.py](/source/07-tracker-delivery/app.py) · [Abrir index.html](/source/07-tracker-delivery/static/index.html)

Cada navegador controla un vehículo sobre un mapa de Puno y todos ven la
flota actualizada en tiempo real. Incluye destinos, ruta visual, distancia,
tiempo estimado, estado del pedido y validación de llegada.

Ejecuta `uvicorn app:app --reload`, abre varias pestañas y usa las flechas del
teclado o los botones. Primero selecciona un destino; la entrega se habilita
cuando el vehículo está suficientemente cerca.


## Ejecutar

```powershell
cd codigo\07-tracker-delivery
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
```python
from math import asin, ceil, cos, radians, sin, sqrt
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


app = FastAPI(title="Tracker Delivery Puno")
BASE_DIR = Path(__file__).parent

MAP_BOUNDS = {
    "west": -70.041,
    "south": -15.850,
    "east": -70.013,
    "north": -15.828,
}
COLORS = ("#f26b38", "#0c9c82", "#3978e8", "#d94f70", "#8b5cf6", "#d6a20e")
VEHICLES = {
    "moto": {"label": "Moto", "speed": 24},
    "bici": {"label": "Bicicleta", "speed": 14},
    "auto": {"label": "Auto", "speed": 30},
}
DESTINATIONS = {
    "base": {
        "id": "base",
        "name": "Base de reparto",
        "address": "Centro de operaciones",
        "lat": -15.8376,
        "lng": -70.0274,
    },
    "plaza": {
        "id": "plaza",
        "name": "Plaza de Armas",
        "address": "Centro historico de Puno",
        "lat": -15.8402,
        "lng": -70.0219,
    },
    "pino": {
        "id": "pino",
        "name": "Parque Pino",
        "address": "Jr. Lima, Puno",
        "lat": -15.8371,
        "lng": -70.0271,
    },
    "terminal": {
        "id": "terminal",
        "name": "Terminal Terrestre",
        "address": "Av. Simon Bolivar, Puno",
        "lat": -15.8465,
        "lng": -70.0214,
    },
    "puerto": {
        "id": "puerto",
        "name": "Puerto de Puno",
        "address": "Bahia interior de Puno",
        "lat": -15.8404,
        "lng": -70.0155,
    },
}
MOVE_STEP = 0.00055
ARRIVAL_RADIUS_KM = 0.13


def clean_text(value: object, fallback: str, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return text or fallback


def number(value: object, fallback: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius = 6371
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lng2 - lng1)
    start_latitude = radians(lat1)
    end_latitude = radians(lat2)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(start_latitude) * cos(end_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius * asin(sqrt(haversine))


class FleetManager:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def add_driver(self, websocket: WebSocket, name: object, vehicle_key: object) -> dict:
        index = len(self.clients)
        selected_vehicle = str(vehicle_key)
        if selected_vehicle not in VEHICLES:
            selected_vehicle = "moto"
        driver = {
            "id": uuid4().hex[:8],
            "name": clean_text(name, "Delivery", 20),
            "color": COLORS[index % len(COLORS)],
            "vehicle": selected_vehicle,
            "lat": -15.8376 - (index % 4) * 0.0007,
            "lng": -70.0274 + (index % 3) * 0.0008,
            "deliveries": 0,
            "distance_travelled": 0.0,
            "destination_id": None,
            "status": "disponible",
        }
        self.clients[websocket] = driver
        return driver

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.pop(websocket, None)

    def public_driver(self, driver: dict) -> dict:
        destination = DESTINATIONS.get(driver["destination_id"])
        remaining = None
        eta_minutes = None
        if destination:
            remaining = distance_km(
                driver["lat"],
                driver["lng"],
                destination["lat"],
                destination["lng"],
            )
            speed = VEHICLES[driver["vehicle"]]["speed"]
            eta_minutes = max(1, ceil((remaining / speed) * 60))
        return {
            **driver,
            "vehicle_label": VEHICLES[driver["vehicle"]]["label"],
            "destination": destination,
            "remaining_km": round(remaining, 2) if remaining is not None else None,
            "eta_minutes": eta_minutes,
            "distance_travelled": round(driver["distance_travelled"], 2),
        }

    async def send_error(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_json({"type": "error", "message": message})

    async def broadcast(self) -> None:
        event = {
            "type": "fleet",
            "drivers": [self.public_driver(driver) for driver in self.clients.values()],
            "stats": {
                "online": len(self.clients),
                "deliveries": sum(driver["deliveries"] for driver in self.clients.values()),
            },
        }
        disconnected: list[WebSocket] = []
        for client in list(self.clients):
            try:
                await client.send_json(event)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(client)
        for client in disconnected:
            self.disconnect(client)


manager = FleetManager()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def tracker_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        first = await websocket.receive_json()
        if not isinstance(first, dict) or first.get("type") != "join":
            await manager.send_error(websocket, "Envia primero el nombre del conductor.")
            return

        driver = manager.add_driver(websocket, first.get("name"), first.get("vehicle"))
        await websocket.send_json(
            {
                "type": "welcome",
                "id": driver["id"],
                "destinations": list(DESTINATIONS.values()),
                "bounds": MAP_BOUNDS,
            }
        )
        await manager.broadcast()

        while True:
            event = await websocket.receive_json()
            if not isinstance(event, dict):
                await manager.send_error(websocket, "El evento debe ser un objeto JSON.")
                continue

            own = manager.clients.get(websocket)
            if not own:
                return
            event_type = event.get("type")

            if event_type == "destination":
                destination_id = str(event.get("destination_id", ""))
                if destination_id not in DESTINATIONS:
                    await manager.send_error(websocket, "Selecciona un destino valido.")
                    continue
                own["destination_id"] = destination_id
                destination = DESTINATIONS[destination_id]
                remaining = distance_km(
                    own["lat"],
                    own["lng"],
                    destination["lat"],
                    destination["lng"],
                )
                own["status"] = "en_destino" if remaining <= ARRIVAL_RADIUS_KM else "en_ruta"
                await manager.broadcast()
            elif event_type == "move":
                previous_lat = own["lat"]
                previous_lng = own["lng"]
                dx = clamp(number(event.get("dx")), -1, 1)
                dy = clamp(number(event.get("dy")), -1, 1)
                own["lat"] = clamp(
                    own["lat"] - dy * MOVE_STEP,
                    MAP_BOUNDS["south"],
                    MAP_BOUNDS["north"],
                )
                own["lng"] = clamp(
                    own["lng"] + dx * MOVE_STEP,
                    MAP_BOUNDS["west"],
                    MAP_BOUNDS["east"],
                )
                own["distance_travelled"] += distance_km(
                    previous_lat,
                    previous_lng,
                    own["lat"],
                    own["lng"],
                )
                destination = DESTINATIONS.get(own["destination_id"])
                if destination:
                    remaining = distance_km(
                        own["lat"],
                        own["lng"],
                        destination["lat"],
                        destination["lng"],
                    )
                    own["status"] = "en_destino" if remaining <= ARRIVAL_RADIUS_KM else "en_ruta"
                await manager.broadcast()
            elif event_type == "deliver":
                destination = DESTINATIONS.get(own["destination_id"])
                if not destination:
                    await manager.send_error(websocket, "Primero selecciona e inicia una ruta.")
                    continue
                remaining = distance_km(
                    own["lat"],
                    own["lng"],
                    destination["lat"],
                    destination["lng"],
                )
                if remaining > ARRIVAL_RADIUS_KM:
                    await manager.send_error(
                        websocket,
                        f"Aun faltan {remaining:.2f} km para completar la entrega.",
                    )
                    continue
                own["deliveries"] += 1
                own["destination_id"] = None
                own["status"] = "disponible"
                await websocket.send_json(
                    {
                        "type": "delivery_complete",
                        "message": f"Entrega completada en {destination['name']}.",
                    }
                )
                await manager.broadcast()
            elif event_type == "reset":
                own["lat"] = DESTINATIONS["base"]["lat"]
                own["lng"] = DESTINATIONS["base"]["lng"]
                own["destination_id"] = None
                own["status"] = "disponible"
                await manager.broadcast()
            else:
                await manager.send_error(websocket, "Evento no reconocido.")
    except WebSocketDisconnect:
        pass
    finally:
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
  <title>Ruta Express Puno</title>
  <style>
    :root {
      --ink:#172923;
      --forest:#17483d;
      --forest-dark:#0b2e27;
      --paper:#faf6ed;
      --cream:#eee7d8;
      --orange:#f26b38;
      --mint:#9ee1c7;
      --blue:#3978e8;
      --muted:#74827d;
      --line:#d9d2c4;
      font-family:"Trebuchet MS","Aptos",sans-serif;
      color:var(--ink);
      background:var(--cream);
    }
    * { box-sizing:border-box; }
    body { min-height:100vh; margin:0; overflow:hidden; background:var(--cream); }
    button,input,select { font:inherit; }
    button { cursor:pointer; }
    .app { display:grid; grid-template-columns:minmax(0,1fr) 370px; height:100vh; }
    .map-panel { position:relative; min-width:0; overflow:hidden; background:#b9c8b5; }
    #map-frame,#routes,#destinations,#drivers { position:absolute; inset:0; width:100%; height:100%; border:0; }
    #map-frame { filter:saturate(.78) contrast(.94) sepia(.08); }
    .map-panel::after { content:""; position:absolute; inset:0; z-index:1; pointer-events:none; background:linear-gradient(180deg,#0b2e2755 0,transparent 25%,transparent 72%,#0b2e2766 100%); }
    #routes { z-index:2; pointer-events:none; filter:drop-shadow(0 2px 2px #fff); }
    #destinations,#drivers { z-index:3; pointer-events:none; }
    .map-head { position:absolute; z-index:5; top:24px; left:28px; display:flex; align-items:center; gap:13px; border:1px solid #ffffff8a; border-radius:19px; padding:12px 15px; color:#fafffc; background:#0b2e27dc; box-shadow:0 16px 40px #102b2460; backdrop-filter:blur(12px); }
    .map-head .logo { display:grid; place-items:center; width:40px; height:40px; border-radius:13px; color:#fff; background:var(--orange); font-family:Georgia,serif; font-size:1.25rem; font-weight:900; transform:rotate(-4deg); }
    .map-head h1 { margin:0; font-family:Georgia,"Palatino Linotype",serif; font-size:1.32rem; letter-spacing:-.045em; }
    .map-head p { margin:2px 0 0; color:#bcd3cc; font-size:.7rem; }
    .connection { position:absolute; z-index:5; top:27px; right:25px; display:flex; align-items:center; gap:7px; border:1px solid #ffffff8a; border-radius:999px; padding:8px 12px; color:#e8f5f0; background:#0b2e27d9; font-size:.7rem; font-weight:850; backdrop-filter:blur(10px); }
    .connection::before { content:""; width:8px; height:8px; border-radius:50%; background:#a0aaa6; }
    .connection[data-state="online"]::before { background:#70e0ae; box-shadow:0 0 0 4px #70e0ae30; }
    .connection[data-state="error"]::before { background:#ff8265; }
    .map-summary { position:absolute; z-index:5; left:28px; bottom:24px; display:grid; grid-template-columns:auto auto auto; gap:18px; border:1px solid #ffffffa0; border-radius:19px; padding:13px 16px; color:#f5fffb; background:#0b2e27e5; box-shadow:0 16px 40px #102b2455; backdrop-filter:blur(12px); }
    .map-summary div { min-width:85px; }
    .map-summary small { display:block; color:#9ebbb2; font-size:.62rem; font-weight:850; letter-spacing:.1em; text-transform:uppercase; }
    .map-summary strong { display:block; margin-top:3px; font-size:.88rem; }
    .osm-credit { position:absolute; z-index:5; right:16px; bottom:10px; border-radius:7px; padding:3px 6px; color:#43534d; background:#fffddd; font-size:.58rem; text-decoration:none; }
    .driver { position:absolute; transform:translate(-50%,-50%); text-align:center; transition:left 130ms linear,top 130ms linear; }
    .driver-pin { position:relative; display:grid; place-items:center; width:43px; height:43px; border:3px solid white; border-radius:16px 16px 16px 4px; color:#fff; background:var(--driver-color); box-shadow:0 8px 24px #19362d70; font-size:1.25rem; transform:rotate(-45deg); }
    .driver-pin span { transform:rotate(45deg); }
    .driver.own .driver-pin { width:49px; height:49px; outline:5px solid #ffffff78; animation:pulse 2s infinite; }
    .driver-label { display:block; margin:8px 0 0; border:1px solid #d9d2c4; border-radius:999px; padding:4px 8px; color:#162a23; background:#fffdf7f2; box-shadow:0 5px 14px #19362d30; font-size:.64rem; font-weight:950; white-space:nowrap; }
    .destination { position:absolute; transform:translate(-50%,-100%); text-align:center; }
    .destination-pin { display:grid; place-items:center; width:29px; height:29px; border:3px solid white; border-radius:50% 50% 50% 5px; color:#fff; background:#172923; box-shadow:0 5px 14px #10271f50; transform:rotate(-45deg); }
    .destination-pin span { transform:rotate(45deg); font-size:.68rem; font-weight:950; }
    .destination label { display:none; margin-top:4px; border-radius:7px; padding:3px 6px; color:#fff; background:#172923da; font-size:.56rem; font-weight:850; white-space:nowrap; }
    .destination.active label { display:inline-block; }
    .dispatch { display:flex; flex-direction:column; min-height:0; border-left:1px solid #d3ccbd; color:var(--ink); background:var(--paper); box-shadow:-18px 0 50px #17292318; }
    .dispatch-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; border-bottom:1px solid var(--line); padding:22px 22px 17px; }
    .eyebrow { display:block; margin-bottom:5px; color:var(--orange); font-size:.62rem; font-weight:950; letter-spacing:.15em; text-transform:uppercase; }
    .dispatch-head h2 { margin:0; font-family:Georgia,"Palatino Linotype",serif; font-size:1.65rem; letter-spacing:-.05em; }
    .dispatch-head button { border:1px solid var(--line); border-radius:10px; padding:7px 9px; color:#56645f; background:#fff; font-size:.66rem; font-weight:850; }
    .scroll-area { min-height:0; overflow:auto; padding:17px 20px 24px; }
    .stats { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
    .stat { border:1px solid var(--line); border-radius:14px; padding:10px; background:#fff; }
    .stat small { display:block; color:var(--muted); font-size:.58rem; font-weight:850; text-transform:uppercase; }
    .stat strong { display:block; margin-top:3px; font-size:1.05rem; }
    .current { margin-top:13px; border-radius:18px; padding:14px; color:#eefaf5; background:linear-gradient(145deg,var(--forest),var(--forest-dark)); box-shadow:0 10px 25px #17483d22; }
    .current-top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
    .current h3 { margin:0; font-size:.95rem; }
    .status-badge { border-radius:999px; padding:5px 8px; color:#0b3429; background:var(--mint); font-size:.58rem; font-weight:950; text-transform:uppercase; }
    .status-badge.route { color:#fff; background:var(--orange); }
    .current-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }
    .current-grid div { border-top:1px solid #ffffff20; padding-top:8px; }
    .current-grid small { display:block; color:#9fc0b6; font-size:.55rem; text-transform:uppercase; }
    .current-grid strong { display:block; margin-top:3px; font-size:.76rem; }
    .section-title { margin:18px 0 8px; color:#65736e; font-size:.62rem; font-weight:950; letter-spacing:.12em; text-transform:uppercase; }
    .route-form { display:grid; grid-template-columns:1fr auto; gap:8px; }
    select { min-width:0; border:1px solid var(--line); border-radius:12px; padding:.76rem .7rem; color:var(--ink); background:#fff; outline:none; }
    select:focus { border-color:#4d9581; box-shadow:0 0 0 3px #9ee1c744; }
    .primary { border:0; border-radius:12px; padding:.75rem .9rem; color:#fff; background:var(--orange); font-weight:900; }
    .control-wrap { display:grid; grid-template-columns:132px 1fr; align-items:center; gap:13px; margin-top:11px; }
    .controls { display:grid; grid-template-columns:repeat(3,40px); justify-content:center; gap:5px; }
    .controls button { height:40px; border:1px solid #cad3cf; border-radius:11px; color:#24453b; background:#fff; font-size:1rem; font-weight:900; box-shadow:0 3px 0 #d8d2c7; }
    .controls button:active { transform:translateY(2px); box-shadow:0 1px 0 #d8d2c7; }
    .actions { display:grid; gap:7px; }
    .actions button { border:1px solid var(--line); border-radius:11px; padding:.65rem .7rem; color:#475852; background:#fff; font-size:.7rem; font-weight:900; }
    .actions .deliver { border-color:#67b895; color:#123d2f; background:#a9e8cd; }
    .actions .deliver:disabled { cursor:not-allowed; opacity:.45; }
    #fleet { display:grid; gap:8px; margin:0; padding:0; list-style:none; }
    #fleet li { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:9px; border:1px solid var(--line); border-radius:13px; padding:9px; background:#fff; }
    .fleet-avatar { display:grid; place-items:center; width:34px; height:34px; border-radius:11px; color:#fff; background:var(--driver-color); font-size:.9rem; }
    .fleet-info strong { display:block; font-size:.76rem; }
    .fleet-info small { display:block; margin-top:2px; color:var(--muted); font-size:.61rem; }
    .fleet-score { color:var(--forest); font-size:.68rem; font-weight:950; }
    .toast { position:fixed; z-index:20; left:50%; bottom:24px; max-width:min(420px,calc(100% - 32px)); border-radius:13px; padding:11px 14px; color:#fff; background:#163c36; box-shadow:0 14px 35px #10271f60; font-size:.76rem; font-weight:850; transform:translate(-50%,120px); opacity:0; transition:.25s ease; }
    .toast.show { transform:translate(-50%,0); opacity:1; }
    .toast.error { background:#9c3d2f; }
    dialog { border:0; border-radius:24px; padding:0; color:var(--ink); background:var(--paper); box-shadow:0 35px 90px #10271fa8; }
    dialog::backdrop { background:#0b2e27c7; backdrop-filter:blur(6px); }
    #login-form { display:grid; gap:14px; width:min(410px,84vw); padding:27px; }
    #login-form h2 { margin:0; font-family:Georgia,"Palatino Linotype",serif; font-size:2rem; letter-spacing:-.05em; }
    #login-form p { margin:-7px 0 3px; color:var(--muted); font-size:.82rem; line-height:1.45; }
    label { display:grid; gap:6px; color:#55645f; font-size:.67rem; font-weight:900; letter-spacing:.06em; text-transform:uppercase; }
    input { border:1px solid var(--line); border-radius:12px; padding:.82rem; color:var(--ink); background:#fff; outline:none; }
    input:focus { border-color:#4d9581; box-shadow:0 0 0 3px #9ee1c744; }
    #login-form button { border:0; border-radius:12px; padding:.86rem; color:#fff; background:var(--forest); font-weight:950; }
    @keyframes pulse { 50% { outline-color:#ffffff20; } }
    @media (max-width:900px) {
      body { overflow:auto; }
      .app { grid-template-columns:1fr; height:auto; min-height:100vh; }
      .map-panel { min-height:61vh; }
      .dispatch { min-height:39vh; border:0; }
      .scroll-area { overflow:visible; }
      .map-summary { left:14px; bottom:14px; gap:10px; }
      .connection { right:14px; }
    }
    @media (max-width:540px) {
      .map-panel { min-height:56vh; }
      .map-head { top:12px; left:12px; padding:9px 11px; }
      .map-head .logo { width:34px; height:34px; }
      .map-head p { display:none; }
      .connection { top:13px; }
      .map-summary { grid-template-columns:repeat(3,1fr); right:14px; }
      .map-summary div { min-width:0; }
      .map-summary strong { font-size:.72rem; }
      .osm-credit { display:none; }
      .dispatch-head { padding:17px 16px 13px; }
      .scroll-area { padding:14px 14px 22px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="map-panel">
      <iframe id="map-frame" title="Mapa de Puno en OpenStreetMap" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox=-70.041%2C-15.850%2C-70.013%2C-15.828&amp;layer=mapnik"></iframe>
      <svg id="routes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"></svg>
      <div id="destinations"></div>
      <div id="drivers"></div>
      <header class="map-head"><span class="logo">R</span><div><h1>Ruta Express Puno</h1><p>Seguimiento colaborativo sobre OpenStreetMap</p></div></header>
      <div id="connection" class="connection" data-state="waiting">Esperando ingreso</div>
      <section class="map-summary">
        <div><small>Destino</small><strong id="summary-destination">Sin ruta</strong></div>
        <div><small>Distancia</small><strong id="summary-distance">-- km</strong></div>
        <div><small>Tiempo estimado</small><strong id="summary-eta">-- min</strong></div>
      </section>
      <a class="osm-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap</a>
    </section>

    <aside class="dispatch">
      <header class="dispatch-head"><div><span class="eyebrow">Centro de operaciones</span><h2>Flota en vivo</h2></div><button id="change-driver" type="button">Cambiar conductor</button></header>
      <div class="scroll-area">
        <section class="stats">
          <div class="stat"><small>En línea</small><strong id="stat-online">0</strong></div>
          <div class="stat"><small>Entregas</small><strong id="stat-deliveries">0</strong></div>
          <div class="stat"><small>Recorrido</small><strong id="stat-distance">0 km</strong></div>
        </section>

        <section class="current">
          <div class="current-top"><h3 id="current-name">Sin conductor</h3><span id="current-status" class="status-badge">Desconectado</span></div>
          <div class="current-grid">
            <div><small>Vehículo</small><strong id="current-vehicle">--</strong></div>
            <div><small>Destino</small><strong id="current-destination">--</strong></div>
            <div><small>Entregas</small><strong id="current-deliveries">0</strong></div>
          </div>
        </section>

        <h3 class="section-title">Nueva ruta</h3>
        <form id="route-form" class="route-form"><select id="destination-select" aria-label="Destino"></select><button class="primary" type="submit">Iniciar</button></form>

        <h3 class="section-title">Mover vehículo</h3>
        <div class="control-wrap">
          <div class="controls">
            <i></i><button data-dx="0" data-dy="-1" aria-label="Mover arriba">↑</button><i></i>
            <button data-dx="-1" data-dy="0" aria-label="Mover izquierda">←</button>
            <button data-dx="0" data-dy="1" aria-label="Mover abajo">↓</button>
            <button data-dx="1" data-dy="0" aria-label="Mover derecha">→</button>
          </div>
          <div class="actions">
            <button id="deliver" class="deliver" type="button" disabled>Completar entrega</button>
            <button id="reset-position" type="button">Volver a la base</button>
          </div>
        </div>

        <h3 class="section-title">Conductores conectados</h3>
        <ul id="fleet"></ul>
      </div>
    </aside>
  </div>

  <dialog id="login" open>
    <form id="login-form">
      <span class="eyebrow">Únete a la flota</span>
      <h2>Configura tu delivery.</h2>
      <p>Elige un conductor y un vehículo. Luego selecciona un destino y recorre Puno con las flechas.</p>
      <label>Nombre del conductor<input id="name" maxlength="20" required autofocus placeholder="Ej. Moto 7"></label>
      <label>Tipo de vehículo<select id="vehicle"><option value="moto">Moto</option><option value="bici">Bicicleta</option><option value="auto">Auto</option></select></label>
      <button type="submit">Entrar al mapa</button>
    </form>
  </dialog>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>

  <script>
    const markerLayer = document.querySelector('#drivers');
    const destinationLayer = document.querySelector('#destinations');
    const routeLayer = document.querySelector('#routes');
    const login = document.querySelector('#login');
    const connection = document.querySelector('#connection');
    const toast = document.querySelector('#toast');
    const destinationSelect = document.querySelector('#destination-select');
    const deliverButton = document.querySelector('#deliver');
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const vehicleIcons = { moto:'●', bici:'◆', auto:'■' };
    const statusLabels = { disponible:'Disponible', en_ruta:'En ruta', en_destino:'En destino' };
    let socket, ownId, profile, destinations = [], latestDrivers = [];
    let bounds = { west:-70.041, south:-15.850, east:-70.013, north:-15.828 };
    let reconnectTimer, moveTimer, leaving = false, toastTimer;

    function coordinates(lat, lng) {
      return {
        x: (lng - bounds.west) * 100 / (bounds.east - bounds.west),
        y: (bounds.north - lat) * 100 / (bounds.north - bounds.south)
      };
    }
    function setConnection(text, state) {
      connection.textContent = text;
      connection.dataset.state = state || 'waiting';
    }
    function showToast(message, error) {
      clearTimeout(toastTimer);
      toast.textContent = message;
      toast.className = 'toast show' + (error ? ' error' : '');
      toastTimer = setTimeout(function() { toast.className = 'toast'; }, 3200);
    }
    function iconFor(vehicle) {
      return vehicleIcons[vehicle] || '●';
    }
    function send(event) {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(event));
    }
    function populateDestinations() {
      destinationSelect.replaceChildren(...destinations.map(function(destination) {
        const option = document.createElement('option');
        option.value = destination.id;
        option.textContent = destination.name;
        return option;
      }));
      destinationLayer.replaceChildren(...destinations.map(function(destination) {
        const point = coordinates(destination.lat, destination.lng);
        const marker = document.createElement('div');
        marker.className = 'destination';
        marker.dataset.destinationId = destination.id;
        marker.style.left = point.x + '%';
        marker.style.top = point.y + '%';
        const pin = document.createElement('div');
        pin.className = 'destination-pin';
        const dot = document.createElement('span');
        dot.textContent = 'D';
        pin.append(dot);
        const label = document.createElement('label');
        label.textContent = destination.name;
        marker.append(pin, label);
        return marker;
      }));
    }
    function routeElement(driver) {
      if (!driver.destination) return null;
      const start = coordinates(driver.lat, driver.lng);
      const end = coordinates(driver.destination.lat, driver.destination.lng);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', start.x);
      line.setAttribute('y1', start.y);
      line.setAttribute('x2', end.x);
      line.setAttribute('y2', end.y);
      line.setAttribute('stroke', driver.color);
      line.setAttribute('stroke-width', driver.id === ownId ? '0.55' : '0.3');
      line.setAttribute('stroke-dasharray', '1.4 1.1');
      line.setAttribute('stroke-linecap', 'round');
      return line;
    }
    function renderMap(drivers) {
      const routes = drivers.map(routeElement).filter(Boolean);
      routeLayer.replaceChildren(...routes);
      markerLayer.replaceChildren(...drivers.map(function(driver) {
        const point = coordinates(driver.lat, driver.lng);
        const marker = document.createElement('div');
        marker.className = 'driver' + (driver.id === ownId ? ' own' : '');
        marker.style.left = point.x + '%';
        marker.style.top = point.y + '%';
        marker.style.setProperty('--driver-color', driver.color);
        const pin = document.createElement('div');
        pin.className = 'driver-pin';
        const icon = document.createElement('span');
        icon.textContent = iconFor(driver.vehicle);
        pin.append(icon);
        const label = document.createElement('span');
        label.className = 'driver-label';
        label.textContent = driver.name + (driver.id === ownId ? ' · tú' : '');
        marker.append(pin, label);
        return marker;
      }));
    }
    function renderFleet(drivers) {
      document.querySelector('#fleet').replaceChildren(...drivers.map(function(driver) {
        const item = document.createElement('li');
        const avatar = document.createElement('span');
        avatar.className = 'fleet-avatar';
        avatar.style.setProperty('--driver-color', driver.color);
        avatar.textContent = iconFor(driver.vehicle);
        const info = document.createElement('div');
        info.className = 'fleet-info';
        const name = document.createElement('strong');
        name.textContent = driver.name + (driver.id === ownId ? ' (tú)' : '');
        const detail = document.createElement('small');
        detail.textContent = driver.destination ? driver.destination.name + ' · ' + driver.remaining_km + ' km' : 'Disponible';
        info.append(name, detail);
        const score = document.createElement('span');
        score.className = 'fleet-score';
        score.textContent = driver.deliveries + ' entregas';
        item.append(avatar, info, score);
        return item;
      }));
    }
    function renderCurrent(driver) {
      if (!driver) return;
      document.querySelector('#current-name').textContent = driver.name;
      document.querySelector('#current-vehicle').textContent = driver.vehicle_label;
      document.querySelector('#current-destination').textContent = driver.destination ? driver.destination.name : 'Sin ruta';
      document.querySelector('#current-deliveries').textContent = driver.deliveries;
      document.querySelector('#stat-distance').textContent = driver.distance_travelled.toFixed(2) + ' km';
      const badge = document.querySelector('#current-status');
      badge.textContent = statusLabels[driver.status] || driver.status;
      badge.className = 'status-badge' + (driver.status === 'disponible' ? '' : ' route');
      document.querySelector('#summary-destination').textContent = driver.destination ? driver.destination.name : 'Sin ruta';
      document.querySelector('#summary-distance').textContent = driver.remaining_km === null ? '-- km' : driver.remaining_km.toFixed(2) + ' km';
      document.querySelector('#summary-eta').textContent = driver.eta_minutes === null ? '-- min' : driver.eta_minutes + ' min';
      deliverButton.disabled = driver.status !== 'en_destino';
      destinationLayer.querySelectorAll('.destination').forEach(function(marker) {
        marker.classList.toggle('active', Boolean(driver.destination && marker.dataset.destinationId === driver.destination.id));
      });
    }
    function renderFleetState(event) {
      latestDrivers = event.drivers;
      renderMap(event.drivers);
      renderFleet(event.drivers);
      renderCurrent(event.drivers.find(function(driver) { return driver.id === ownId; }));
      document.querySelector('#stat-online').textContent = event.stats.online;
      document.querySelector('#stat-deliveries').textContent = event.stats.deliveries;
      setConnection(event.stats.online + ' vehículo' + (event.stats.online === 1 ? '' : 's') + ' en línea', 'online');
    }
    function connect() {
      if (!profile) return;
      clearTimeout(reconnectTimer);
      setConnection('Conectando...', 'waiting');
      const nextSocket = new WebSocket(protocol + '://' + location.host + '/ws');
      socket = nextSocket;
      nextSocket.addEventListener('open', function() {
        nextSocket.send(JSON.stringify({ type:'join', name:profile.name, vehicle:profile.vehicle }));
      });
      nextSocket.addEventListener('message', function(message) {
        const event = JSON.parse(message.data);
        if (event.type === 'welcome') {
          ownId = event.id;
          destinations = event.destinations;
          bounds = event.bounds;
          populateDestinations();
          login.close();
          setConnection('Conectado', 'online');
        } else if (event.type === 'fleet') {
          renderFleetState(event);
        } else if (event.type === 'delivery_complete') {
          showToast(event.message, false);
        } else if (event.type === 'error') {
          showToast(event.message || 'No se pudo completar la acción.', true);
        }
      });
      nextSocket.addEventListener('close', function() {
        if (socket !== nextSocket || leaving || !profile) return;
        setConnection('Reconectando...', 'error');
        reconnectTimer = setTimeout(connect, 1400);
      });
      nextSocket.addEventListener('error', function() {
        setConnection('Sin conexión', 'error');
      });
    }
    function move(dx, dy) {
      send({ type:'move', dx:dx, dy:dy });
    }
    function startMoving(button) {
      const dx = Number(button.dataset.dx);
      const dy = Number(button.dataset.dy);
      move(dx, dy);
      clearInterval(moveTimer);
      moveTimer = setInterval(function() { move(dx, dy); }, 115);
    }
    function stopMoving() {
      clearInterval(moveTimer);
    }

    document.querySelector('#login-form').addEventListener('submit', function(event) {
      event.preventDefault();
      profile = {
        name:document.querySelector('#name').value.trim(),
        vehicle:document.querySelector('#vehicle').value
      };
      leaving = false;
      connect();
    });
    document.querySelector('#route-form').addEventListener('submit', function(event) {
      event.preventDefault();
      send({ type:'destination', destination_id:destinationSelect.value });
      showToast('Ruta iniciada. Sigue la línea punteada.', false);
    });
    document.querySelectorAll('[data-dx]').forEach(function(button) {
      button.addEventListener('pointerdown', function(event) {
        event.preventDefault();
        startMoving(button);
      });
      button.addEventListener('pointerup', stopMoving);
      button.addEventListener('pointerleave', stopMoving);
      button.addEventListener('pointercancel', stopMoving);
    });
    deliverButton.addEventListener('click', function() { send({ type:'deliver' }); });
    document.querySelector('#reset-position').addEventListener('click', function() {
      send({ type:'reset' });
      showToast('Vehículo reubicado en la base de reparto.', false);
    });
    document.querySelector('#change-driver').addEventListener('click', function() {
      leaving = true;
      clearTimeout(reconnectTimer);
      stopMoving();
      if (socket) socket.close();
      profile = null;
      ownId = null;
      latestDrivers = [];
      markerLayer.replaceChildren();
      routeLayer.replaceChildren();
      destinationLayer.replaceChildren();
      setConnection('Esperando ingreso', 'waiting');
      login.showModal();
    });
    addEventListener('keydown', function(event) {
      const moves = { ArrowUp:[0,-1], ArrowDown:[0,1], ArrowLeft:[-1,0], ArrowRight:[1,0] };
      if (moves[event.key]) {
        event.preventDefault();
        move(moves[event.key][0], moves[event.key][1]);
      }
    });
    addEventListener('pointerup', stopMoving);
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

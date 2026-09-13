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

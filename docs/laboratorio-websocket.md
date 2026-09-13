# WebSocket esencial y laboratorio

<div class="module-banner">
  <span class="eyebrow">Módulo 1 · 20 minutos</span>
  <h2>De una conexión abierta a una aplicación en tiempo real</h2>
  <p>Veremos únicamente lo necesario para comprender el chat, WPlace, las reacciones, el tracker y los demás proyectos.</p>
</div>

Al finalizar, dos pestañas podrán intercambiar eventos inmediatamente mediante una sola aplicación FastAPI.

## 1. HTTP y WebSocket no hacen lo mismo

| HTTP tradicional | WebSocket |
|---|---|
| El cliente realiza una petición y recibe una respuesta. | Cliente y servidor mantienen una conexión abierta. |
| Sirve para cargar páginas, consultar o guardar datos. | Sirve para chat, tableros, posiciones y eventos en vivo. |
| Para obtener cambios nuevos hay que volver a consultar. | El servidor puede enviar un cambio sin esperar otra petición. |

WebSocket **no significa varios servidores**. Una sola instancia de FastAPI puede mantener muchas conexiones simultáneas.

## 2. El recorrido de un evento

<div class="architecture-flow" aria-label="Recorrido de un evento WebSocket">
  <span>Navegador A</span><b>→</b><span>FastAPI</span><b>→</b><span>Broadcast</span><b>→</b><span>Navegadores</span>
</div>

Usaremos mensajes JSON porque son fáciles de leer desde Python y JavaScript:

```json
{
  "type": "message",
  "user": "grupo-3",
  "text": "¡Funciona!"
}
```

El campo `type` indica qué ocurrió. El resto contiene los datos del evento.

| Proyecto | Evento principal | Datos enviados |
|---|---|---|
| Chat | `message` | Usuario y texto. |
| WPlace | `paint` | Posición y color. |
| Cursor Party | `move` | Coordenadas del cursor. |
| Encuesta | `vote` | Opción seleccionada. |
| Tracker | `location` | Latitud, longitud o posición simulada. |
| Subasta | `bid` | Usuario y nueva oferta. |

## 3. Las cuatro acciones del servidor

```python
await websocket.accept()             # 1. acepta al cliente
event = await websocket.receive_json()  # 2. recibe un evento
await client.send_json(event)        # 3. envía el evento
connections.remove(websocket)        # 4. retira al desconectado
```

El administrador conserva las conexiones activas y realiza el broadcast:

```python
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
        for connection in self.active_connections:
            await connection.send_json(event)
```

`broadcast` recorre la lista y entrega el mismo evento a todos. Eso permite que cada pestaña vea el mismo estado.

## 4. La conexión desde JavaScript

```javascript
const socket = new WebSocket(`ws://${location.host}/ws`)

socket.onopen = () => {
  console.log('Conectado')
  socket.send(JSON.stringify({
    type: 'message',
    user: 'grupo-3',
    text: 'Hola',
  }))
}

socket.onmessage = (message) => {
  const event = JSON.parse(message.data)
  console.log(event)
}

```

| Acción | JavaScript | FastAPI |
|---|---|---|
| Conectar | `new WebSocket(...)` | `await websocket.accept()` |
| Enviar | `socket.send(...)` | `receive_json()` |
| Recibir | `socket.onmessage` | `send_json()` |
| Cerrar | `socket.close()` | `WebSocketDisconnect` |

## 5. Ejecutar el laboratorio

[Descargar código base](/downloads/01-websocket-base.zip) · [Ver código completo](/codigo/01-websocket-base.html)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre dos pestañas en [http://127.0.0.1:8000](http://127.0.0.1:8000). Envía un mensaje desde una y comprueba que aparece en ambas.

## 6. Reto de cinco minutos

Modifica el evento para incluir el nombre del grupo y prueba:

- Dos pestañas enviando mensajes a la vez.
- Una pestaña cerrándose sin detener a las demás.
- Un texto vacío que el servidor debe rechazar.
- Un nuevo evento `reaction` con un emoji.

## Errores frecuentes

| Problema | Causa probable | Solución rápida |
|---|---|---|
| No conecta | El servidor no está ejecutándose. | Revisa la terminal y abre nuevamente `127.0.0.1:8000`. |
| Solo cambia una pestaña | El frontend actualiza localmente, pero no hace broadcast. | Envía el evento desde FastAPI a todas las conexiones. |
| Aparece un error JSON | Se envió texto sin convertirlo a JSON. | Usa `JSON.stringify()` al enviar y `JSON.parse()` al recibir. |
| Falla al cerrar una pestaña | No se controló la desconexión. | Captura `WebSocketDisconnect` y retira la conexión. |

::: tip Punto de control
WebSocket mantiene la conexión abierta. FastAPI recibe eventos, conserva los clientes activos y hace broadcast para todas las conexiones activas.
:::

[Elegir un proyecto →](/proyectos/)

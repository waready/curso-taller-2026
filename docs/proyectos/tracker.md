# Tracker Delivery Puno

[Abrir demo en Vercel](https://curso-taller-07-tracker-delivery.vercel.app) · [Descargar proyecto](/downloads/07-tracker-delivery.zip) · [Ver código completo](/codigo/07-tracker-delivery.html)

Cada pestaña controla una moto, bicicleta o auto sobre OpenStreetMap en Puno.
Todos observan la flota, los destinos, las rutas y el número de entregas en
vivo. La aplicación calcula distancia y tiempo estimado, y solo permite
completar un pedido al llegar al destino.

## Evento principal

```json
{"type":"destination","destination_id":"terminal"}
```

FastAPI asigna el destino, valida cada movimiento, calcula la distancia
restante y transmite la flota completa por WebSocket.

## Reto del grupo

Agrega pedidos aleatorios, una tabla de posiciones o persistencia del historial de entregas.

# Ruta práctica de 4 horas

La clase sigue una sola idea y la transforma varias veces: **conectar → enviar evento → guardar estado → transmitir a todos**. No empezamos ocho proyectos desde cero.

<div class="schedule-grid">
  <div class="schedule-card"><span class="time-pill">00:00–00:30</span><strong>Python esencial</strong><span>Variables, colecciones, funciones, clases, decoradores y async/await con ejercicios breves.</span></div>
  <div class="schedule-card"><span class="time-pill">00:30–00:50</span><strong>FastAPI + WebSocket</strong><span>Levantamos el servidor y comprobamos el mismo evento en dos pestañas.</span></div>
  <div class="schedule-card"><span class="time-pill">00:50–01:15</span><strong>Reacciones en vivo</strong><span>Botones, emojis, contador colectivo y broadcast.</span></div>
  <div class="schedule-card"><span class="time-pill">01:15–01:45</span><strong>Chat con presencia</strong><span>Nombres, mensajes, entradas, salidas y “está escribiendo”.</span></div>
  <div class="schedule-card"><span class="time-pill">01:45–02:25</span><strong>Mini-WPlace</strong><span>Estado compartido, validación y tablero recuperable al recargar.</span></div>
  <div class="schedule-card"><span class="time-pill">02:25–03:10</span><strong>Reto divertido por grupos</strong><span>Encuesta, Cursor Party, tracker tipo Uber o subasta flash.</span></div>
  <div class="schedule-card"><span class="time-pill">03:10–03:45</span><strong>Mejora con IA</strong><span>Codex o Claude Code implementa una mejora pequeña que el grupo debe probar.</span></div>
  <div class="schedule-card"><span class="time-pill">03:45–04:00</span><strong>Demo relámpago</strong><span>Cada grupo muestra el resultado y explica el evento principal.</span></div>
</div>

## Solo la teoría necesaria

| Idea | Ejemplo visible |
|---|---|
| Cliente y servidor | Dos navegadores se comunican a través de FastAPI. |
| WebSocket | La conexión permanece abierta y permite enviar en ambos sentidos. |
| Evento JSON | `chat`, `vote`, `paint`, `move` o `bid`. |
| Concurrencia | Varias personas interactúan al mismo tiempo. |
| Estado compartido | El servidor recuerda mensajes, votos, píxeles o posiciones. |
| Broadcast | Un cambio llega a todas las conexiones activas. |
| Desconexión | Un usuario sale sin detener a los demás. |

::: tip Una instancia es suficiente
En estas prácticas una sola aplicación FastAPI atiende muchas conexiones y conserva el estado compartido durante la actividad.
:::

## Reto por grupos

Cada grupo parte del código completo y elige **una mejora**:

- Cursor Party: dejar una estela o dibujar juntos.
- Tracker: agregar destino y tiempo estimado.
- Subasta: temporizador o cierre automático.
- WPlace: enfriamiento, contador o botón de descarga.
- Chat: salas o reacciones por mensaje.

El asistente de IA puede editar, pero el grupo debe explicar qué evento envió, qué validó el servidor y qué recibieron los demás clientes.

[Usar los prompts listos para Codex o Claude Code →](/ia.html)

[Ver las demos y elegir →](/proyectos/)

[Repasar Python esencial →](/python-esencial.html) · [Aprender WebSocket esencial →](/laboratorio-websocket.html)

# Proyecto A: Chat con presencia

[Abrir demo en Vercel](https://curso-taller-02-chat-tiempo-real.vercel.app) · [Descargar proyecto](/downloads/02-chat-tiempo-real.zip) · [Ver código completo](/codigo/02-chat-tiempo-real.html)

## Meta mínima

- Ingresar con un nombre.
- Enviar mensajes a todos.
- Mostrar cuántas personas están conectadas.
- Notificar entradas y salidas.

## Eventos

```json
{"type":"join","user":"Ana"}
{"type":"message","user":"Ana","text":"Hola equipo"}
{"type":"typing","user":"Ana","active":true}
```

## Orden de construcción

1. Prueba el chat en dos pestañas.
2. Encuentra `ConnectionManager` en `app.py`.
3. Agrega la notificación “usuario conectado”.
4. Rechaza nombres y mensajes vacíos.
5. Elige una mejora.

## Mejora con IA — elegir una

- Mostrar “Ana está escribiendo…”.
- Agregar reacciones 👍 ❤️ 😂 a cada mensaje.
- Crear salas mediante un código corto.
- Mostrar hora local en cada mensaje.

Prompt sugerido:

```text
Lee app.py y static/index.html. Antes de editar, explícame cómo viaja un evento
desde un navegador hasta los demás. Luego agrega el indicador "está escribiendo"
usando eventos WebSocket JSON. Haz el cambio mínimo y no agregues dependencias.
```

## Prueba final

Abre tres pestañas, entra con nombres diferentes, cierra una y verifica que el contador se actualice sin reiniciar el servidor.

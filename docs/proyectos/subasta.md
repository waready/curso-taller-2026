# Subasta Flash

[Abrir demo en Vercel](https://curso-taller-08-subasta-flash.vercel.app) · [Descargar proyecto](/downloads/08-subasta-flash.zip) · [Ver código completo](/codigo/08-subasta-flash.html)

Los participantes compiten por una caja misteriosa. El servidor decide qué puja es válida, conserva al líder y sincroniza el historial.

## Evento principal

```json
{"type":"bid","amount":180}
```

Las pujas menores al precio actual o demasiado grandes se rechazan solamente para quien las envió.

## Reto del grupo

Agrega un temporizador, un botón de puja rápida o un cierre automático que anuncie al ganador.

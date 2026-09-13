# Proyecto C: Reacciones en vivo

[Abrir demo en Vercel](https://curso-taller-04-reacciones-en-vivo.vercel.app) · [Descargar proyecto](/downloads/04-reacciones-en-vivo.zip) · [Ver código completo](/codigo/04-reacciones-en-vivo.html)

## Idea

Una persona proyecta la pantalla y el público pulsa emojis desde otros navegadores. Cada reacción aparece como una animación y aumenta el contador colectivo.

## Meta mínima

- Cuatro botones de reacción.
- Animación al recibir un evento.
- Conteo global sincronizado.
- Botón de reinicio solo para la demostración.

## Evento principal

```json
{"type":"reaction","emoji":"🔥"}
```

El servidor actualiza el estado y responde:

```json
{
  "type":"reaction",
  "emoji":"🔥",
  "counts":{"🔥":18,"👏":11,"🤯":7,"❤️":15}
}
```

## Orden de construcción

1. Envía reacciones desde tres pestañas.
2. Identifica dónde se incrementa el contador.
3. Rechaza emojis que no estén permitidos.
4. Agrega una mejora.

## Mejora con IA — elegir una

- Mostrar la reacción más popular.
- Limitar a cinco reacciones por segundo y conexión.
- Añadir preguntas con votación A/B/C/D.
- Cambiar el fondo según el ánimo colectivo.

Prompt sugerido:

```text
Agrega a este muro una pregunta con cuatro alternativas. Cada conexión puede
votar una vez. Todos deben ver los resultados en tiempo real. Reutiliza el
WebSocket existente y no agregues librerías.
```

## Prueba final

Deja una pestaña visible. El grupo envía veinte reacciones desde varios navegadores y explica qué parte del servidor conserva el conteo.

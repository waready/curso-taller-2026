# Proyecto B: WPlace colaborativo

[Abrir demo en Vercel](https://curso-taller-03-wplace-colaborativo.vercel.app) · [Descargar proyecto](/downloads/03-wplace-colaborativo.zip) · [Ver código completo](/codigo/03-wplace-colaborativo.html)

## Meta mínima

- Ver una cuadrícula de píxeles.
- Elegir un color.
- Pintar una celda.
- Ver el cambio en todos los navegadores.
- Recibir el tablero completo al conectarse.

## Eventos

```json
{"type":"paint","x":8,"y":4,"color":"#15d1c5"}
{"type":"board","pixels":["#07111f","#07111f","#15d1c5"]}
```

## Estado compartido

El servidor mantiene una lista con los colores. Para una cuadrícula de 20 × 20:

```python
BOARD_SIZE = 20
board = ["#111827"] * (BOARD_SIZE * BOARD_SIZE)
```

El índice de una celda se obtiene con:

```python
index = y * BOARD_SIZE + x
```

## Orden de construcción

1. Abre el tablero en dos pestañas.
2. Pinta y observa el evento `paint`.
3. Valida límites y colores en el servidor.
4. Comprueba que un usuario nuevo recibe el estado actual.
5. Elige una mejora.

## Mejora con IA — elegir una

- Bloqueo de cinco segundos entre píxeles.
- Contador de píxeles por usuario.
- Botón para descargar el tablero como PNG.
- Historial y botón “deshacer último píxel”.

Prompt sugerido:

```text
Analiza este WPlace pequeño. Agrega un enfriamiento de 5 segundos por usuario.
El servidor debe decidir si acepta el píxel y enviar un evento de error solamente
al usuario que debe esperar. Mantén el estado del tablero en el servidor.
```

## Prueba final

Entre todos dibujen una figura simple. Un integrante recarga la página y debe recuperar el tablero actual.

# Cartas Casino

[Abrir demo en Vercel](https://curso-taller-09-cartas-casino.vercel.app) · [Ver codigo completo](/codigo/09-cartas-casino.html)

Todos ven las mismas dos cartas, A y B. Cada jugador elige una caja de apuesta
y una carta durante ocho segundos. Cuando las cartas se revelan, quienes apostaron
por la carta mayor cobran el doble; si hay empate, se devuelve la apuesta.

## Evento de apuesta

```json
{"type":"bet","amount":5,"side":"a"}
```

Los resultados se muestran por cuatro segundos y luego comienza una ronda nueva.

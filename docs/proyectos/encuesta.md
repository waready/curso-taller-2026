# Encuesta Battle

[Abrir demo en Vercel](https://curso-taller-05-encuesta-battle.vercel.app) · [Descargar proyecto](/downloads/05-encuesta-battle.zip) · [Ver código completo](/codigo/05-encuesta-battle.html)

Cuatro opciones compiten con barras animadas. Cada conexión puede votar y cambiar su voto; todos ven el resultado inmediatamente.

## Evento principal

```json
{"type":"vote","option":"wplace"}
```

El servidor relaciona la conexión con su voto, recalcula los conteos y transmite un evento `state`.

## Reto del grupo

Agrega una pregunta propia, bloquea el cambio de voto o muestra al ganador con una animación.

# Cursor Party

[Abrir demo en Vercel](https://curso-taller-06-cursor-party.vercel.app) · [Descargar proyecto](/downloads/06-cursor-party.zip) · [Ver código completo](/codigo/06-cursor-party.html)

Cada persona entra con un nombre y una sala. Comparte un cursor con color,
puede dibujar líneas con grosor variable y deshacer solo su último trazo.
Las salas están aisladas y quien la crea es la única persona que puede
limpiar la pizarra completa.

## Evento principal

```json
{"type":"draw","x1":42.5,"y1":68.1,"x2":49.2,"y2":72.4,"width":0.8}
```

El servidor conserva los cursores, las líneas y el creador de cada sala.
Luego transmite el estado actualizado solo a las personas de esa sala.

## Reto del grupo

Agrega una descarga PNG, una paleta de color por usuario o una zona que todos deban ocupar para ganar.

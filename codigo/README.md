# Código del taller

Cada carpeta es un proyecto independiente y puede ejecutarse con los mismos pasos.

## Proyectos incluidos

1. `01-websocket-base`: conexión, broadcast y presencia.
2. `02-chat-tiempo-real`: chat, usuarios y “está escribiendo”.
3. `03-wplace-colaborativo`: tablero de píxeles compartido.
4. `04-reacciones-en-vivo`: emojis y conteos instantáneos.
5. `05-encuesta-battle`: votación con resultados animados.
6. `06-cursor-party`: cursores compartidos en una pantalla.
7. `07-tracker-delivery`: vehículos y entregas tipo Uber.
8. `08-subasta-flash`: pujas, líder e historial.

9. `09-cartas-casino`: apuestas por Carta A o B con rondas compartidas.
10. OpenAI Lab con FastAPI: modulos de texto, audio, imagen y vision.

## Windows PowerShell

```powershell
cd 01-websocket-base
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre `http://127.0.0.1:8000` en dos pestañas.

## macOS o Linux

```bash
cd 01-websocket-base
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app:app --reload
```

Para cambiar de proyecto, detén el servidor con `Ctrl + C`, entra a otra carpeta y vuelve a ejecutar `uvicorn app:app --reload`.

Para compartir una demo dentro de la misma red, ejecuta `python -m uvicorn app:app --host 0.0.0.0 --port 8000` y comparte la dirección IPv4 de la computadora que actúa como servidor.

Nunca guardes una API key dentro de estas carpetas.

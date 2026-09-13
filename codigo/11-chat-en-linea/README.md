# 11 - Chat en linea

Chat con FastAPI y WebSocket que incluye salas, usuarios conectados, historial
reciente, indicador de escritura y reconexion automatica.

## Ejecutar

~~~powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8002
~~~

Abre http://127.0.0.1:8002 en dos pestañas, usa nombres diferentes y escribe
el mismo nombre de sala.

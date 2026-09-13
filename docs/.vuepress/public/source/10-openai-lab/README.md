# 10 - OpenAI Lab con FastAPI

Replica de los modulos de ReactGPT, pero con un solo proyecto FastAPI que
sirve el frontend y el backend. Incluye correccion, pros y contras, streaming,
traduccion, texto a audio, audio a texto, generar y editar imagenes, vision y
un asistente conversacional.

Al abrir la pagina se solicita una clave de OpenAI. Es un modo de practica:
la clave se mantiene solo en memoria en esa pestana, se envia en la cabecera
X-OpenAI-Key de cada solicitud y no se escribe en SQLite, archivos ni
registros de la aplicacion.

No lo publiques por HTTP ni lo uses como patron de produccion. Para una
aplicacion real, la clave pertenece exclusivamente al servidor y debe
protegerse con autenticacion, limites de uso y HTTPS.

## Ejecutar

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m uvicorn app:app --reload

Abre http://127.0.0.1:8000 y pega una clave de prueba al inicio.

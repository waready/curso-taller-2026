# OpenAI Lab con FastAPI — código completo

[Ver proyecto completo en GitHub](https://github.com/waready/curso-taller-2026/tree/main/codigo/10-openai-lab) · [Descargar ZIP](/downloads/10-openai-lab.zip) · [Abrir app.py](/source/10-openai-lab/app.py) · [Abrir index.html](/source/10-openai-lab/static/index.html)

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


## Ejecutar

```powershell
cd codigo\10-openai-lab
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
```python
from __future__ import annotations

import base64
import json
from collections.abc import Generator
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response, StreamingResponse
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field


app = FastAPI(title="OpenAI Lab con FastAPI")
BASE_DIR = Path(__file__).parent
TEXT_MODEL = "gpt-4.1-mini"
IMAGE_MODEL = "gpt-image-2"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=6000)


class TranslateRequest(PromptRequest):
    target_language: str = Field(min_length=2, max_length=60)


class SpeechRequest(PromptRequest):
    voice: Literal["alloy", "ash", "coral", "echo", "nova", "sage", "shimmer"] = "alloy"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantRequest(PromptRequest):
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


def require_openai_key(
    x_openai_key: Annotated[str | None, Header(alias="X-OpenAI-Key")] = None,
) -> str:
    if not x_openai_key or not x_openai_key.strip():
        raise HTTPException(status_code=401, detail="Ingresa una clave de OpenAI para continuar.")
    return x_openai_key.strip()


def openai_client(
    api_key: Annotated[str, Depends(require_openai_key)],
) -> Generator[OpenAI, None, None]:
    """Creates one client per non-streaming request without storing the key."""
    client = OpenAI(api_key=api_key)
    try:
        yield client
    finally:
        client.close()


def api_error(error: Exception) -> HTTPException:
    if isinstance(error, AuthenticationError):
        return HTTPException(status_code=401, detail="La clave de OpenAI no es valida.")
    if isinstance(error, RateLimitError):
        return HTTPException(status_code=429, detail="La clave alcanzo su limite o no tiene saldo disponible.")
    if isinstance(error, APIConnectionError):
        return HTTPException(status_code=503, detail="No fue posible conectar con OpenAI. Intenta otra vez.")
    if isinstance(error, APIStatusError):
        body = getattr(error, "body", None)
        message = ""
        if isinstance(body, dict):
            payload = body.get("error", body)
            if isinstance(payload, dict):
                message = str(payload.get("message", "")).strip()
        message = message or str(getattr(error, "message", "")).strip()
        if error.status_code < 500 and message:
            return HTTPException(status_code=error.status_code, detail=f"OpenAI rechazo la solicitud: {message}")
        return HTTPException(status_code=error.status_code, detail="OpenAI no pudo completar esta solicitud.")
    return HTTPException(status_code=502, detail="No fue posible procesar la solicitud con OpenAI.")


async def run_openai(task):
    try:
        return await run_in_threadpool(task)
    except HTTPException:
        raise
    except Exception as error:
        raise api_error(error) from None


def ask_text(client: OpenAI, prompt: str, instructions: str) -> str:
    response = client.responses.create(
        model=TEXT_MODEL,
        instructions=instructions,
        input=prompt,
        max_output_tokens=1200,
        store=False,
    )
    return response.output_text.strip()


def parse_json_output(text: str) -> dict | None:
    cleaned = text.strip()
    fence = chr(96) * 3
    if cleaned.startswith(fence):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith(fence):
            cleaned = cleaned.rstrip()[:-3]

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None

    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def image_url_from_response(response) -> dict[str, str]:
    image = response.data[0]
    base64_image = getattr(image, "b64_json", None)
    if base64_image:
        return {
            "image_url": f"data:image/png;base64,{base64_image}",
            "revised_prompt": getattr(image, "revised_prompt", "") or "",
        }
    return {
        "image_url": getattr(image, "url", "") or "",
        "revised_prompt": getattr(image, "revised_prompt", "") or "",
    }


async def read_upload(file: UploadFile, prefix: str) -> tuple[str, bytes, str]:
    if not file.content_type or not file.content_type.startswith(prefix):
        raise HTTPException(status_code=415, detail=f"Selecciona un archivo {prefix} valido.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="El archivo esta vacio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el limite de 10 MB.")
    return file.filename or "archivo", content, file.content_type


def detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


async def read_image_upload(file: UploadFile) -> tuple[str, bytes, str]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="El archivo esta vacio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el limite de 10 MB.")

    content_type = detect_image_type(content)
    if not content_type:
        raise HTTPException(
            status_code=415,
            detail="Selecciona una imagen JPG, PNG o WebP valida.",
        )

    stem = Path(file.filename or "imagen").stem or "imagen"
    return f"{stem}{IMAGE_EXTENSIONS[content_type]}", content, content_type


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "storage": "La clave no se guarda en el servidor."}


@app.post("/api/orthography")
async def orthography(
    body: PromptRequest, client: OpenAI = Depends(openai_client)
) -> dict:
    instructions = (
        "Eres un corrector de espanol. Devuelve un objeto JSON valido, sin "
        "bloques Markdown ni texto extra. Usa exactamente las claves score "
        "(numero de 0 a 100), corrections (lista de textos) y message "
        "(texto corto y amable). Corrige ortografia y gramatica."
    )
    text = await run_openai(lambda: ask_text(client, body.prompt, instructions))
    parsed = parse_json_output(text)
    if not parsed:
        return {"score": 0, "corrections": [], "message": text}

    corrections = parsed.get("corrections", parsed.get("errors", []))
    if not isinstance(corrections, list):
        corrections = [str(corrections)]
    try:
        score = max(0, min(100, round(float(parsed.get("score", parsed.get("userScore", 0))))))
    except (TypeError, ValueError):
        score = 0
    return {
        "score": score,
        "corrections": [str(item) for item in corrections],
        "message": str(parsed.get("message", "Revision completada.")),
    }


@app.post("/api/pros-cons")
async def pros_cons(
    body: PromptRequest, client: OpenAI = Depends(openai_client)
) -> dict[str, str]:
    instructions = (
        "Analiza la propuesta de forma equilibrada. Usa los titulos Pros, Contras "
        "y Recomendacion. Escribe en espanol y usa listas cortas."
    )
    text = await run_openai(lambda: ask_text(client, body.prompt, instructions))
    return {"text": text}


def stream_discussion(api_key: str, prompt: str):
    instructions = (
        "Analiza la propuesta de forma equilibrada. Escribe en espanol, con "
        "Pros, Contras y una Recomendacion final. Usa listas cortas."
    )
    client = OpenAI(api_key=api_key)
    try:
        stream = client.responses.create(
            model=TEXT_MODEL,
            instructions=instructions,
            input=prompt,
            max_output_tokens=1200,
            stream=True,
            store=False,
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
    except Exception:
        yield "\n\nNo fue posible completar el streaming. Revisa la clave, cuota y conexion."
    finally:
        client.close()


@app.post("/api/pros-cons-stream")
async def pros_cons_stream(
    body: PromptRequest, api_key: str = Depends(require_openai_key)
) -> StreamingResponse:
    return StreamingResponse(
        stream_discussion(api_key, body.prompt),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/api/translate")
async def translate(
    body: TranslateRequest, client: OpenAI = Depends(openai_client)
) -> dict[str, str]:
    instructions = (
        f"Traduce el texto al idioma {body.target_language}. Conserva el tono, "
        "nombres propios y formato. Responde solo con la traduccion."
    )
    text = await run_openai(lambda: ask_text(client, body.prompt, instructions))
    return {"text": text}


@app.post("/api/text-to-audio")
async def text_to_audio(
    body: SpeechRequest, client: OpenAI = Depends(openai_client)
) -> Response:
    def create_speech() -> bytes:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=body.voice,
            input=body.prompt,
            response_format="mp3",
        )
        return speech.content

    audio = await run_openai(create_speech)
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/audio-to-text")
async def audio_to_text(
    file: UploadFile = File(...),
    prompt: str = Form(""),
    client: OpenAI = Depends(openai_client),
) -> dict[str, str]:
    filename, content, content_type = await read_upload(file, "audio/")

    def transcribe() -> str:
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(filename, content, content_type),
            prompt=prompt or None,
        )
        return result.text

    text = await run_openai(transcribe)
    return {"text": text}


@app.post("/api/image-generation")
async def image_generation(
    body: PromptRequest, client: OpenAI = Depends(openai_client)
) -> dict[str, str]:
    def generate() -> dict[str, str]:
        response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=body.prompt,
            size="1024x1024",
            quality="low",
            output_format="png",
        )
        return image_url_from_response(response)

    return await run_openai(generate)


@app.post("/api/image-edit")
async def image_edit(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    mask: UploadFile | None = File(None),
    client: OpenAI = Depends(openai_client),
) -> dict[str, str]:
    filename, content, content_type = await read_image_upload(image)
    mask_data = None
    if mask:
        mask_filename, mask_content, mask_type = await read_image_upload(mask)
        mask_data = (mask_filename, mask_content, mask_type)

    def edit() -> dict[str, str]:
        options = {
            "model": IMAGE_MODEL,
            "image": (filename, content, content_type),
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "low",
            "output_format": "png",
        }
        if mask_data:
            options["mask"] = mask_data
        response = client.images.edit(**options)
        return image_url_from_response(response)

    return await run_openai(edit)


@app.post("/api/image-to-text")
async def image_to_text(
    prompt: str = Form(""),
    image: UploadFile = File(...),
    client: OpenAI = Depends(openai_client),
) -> dict[str, str]:
    _, content, content_type = await read_image_upload(image)
    data_url = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"

    def describe() -> str:
        response = client.responses.create(
            model=TEXT_MODEL,
            instructions="Responde en espanol de manera clara y util.",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt or "Describe y extrae el texto importante de esta imagen.",
                        },
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            max_output_tokens=1400,
            store=False,
        )
        return response.output_text.strip()

    text = await run_openai(describe)
    return {"text": text}


@app.post("/api/assistant")
async def assistant(
    body: AssistantRequest, client: OpenAI = Depends(openai_client)
) -> dict[str, str]:
    transcript = "\n".join(
        f"{message.role.title()}: {message.content}" for message in body.history[-12:]
    )
    prompt = f"{transcript}\nUser: {body.prompt}".strip()
    instructions = (
        "Eres un asistente util para estudiantes de tecnologia. Responde en "
        "espanol, de forma concreta y sin inventar datos."
    )
    text = await run_openai(lambda: ask_text(client, prompt, instructions))
    return {"text": text}
```
:::

::: details static/index.html — frontend completo
```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenAI Lab · FastAPI</title>
  <style>
    :root { --ink:#17302b; --muted:#65746e; --paper:#f5f1e8; --panel:#fffdf8; --line:#d9d5ca; --leaf:#1e6b54; --lime:#d6ef9b; --orange:#ef8054; --blue:#97cce5; font-family:"Trebuchet MS",sans-serif; color:var(--ink); background:var(--paper); }
    * { box-sizing:border-box; }
    body { min-height:100vh; margin:0; background:radial-gradient(circle at 8% 0%,#d6ef9b 0,transparent 24rem),radial-gradient(circle at 90% 90%,#97cce5 0,transparent 30rem),var(--paper); }
    button,input,textarea,select { font:inherit; }
    button { cursor:pointer; }
    .shell { display:grid; grid-template-columns:272px minmax(0,1fr); min-height:100vh; }
    aside { padding:24px 17px; color:#eef6ed; background:#173b32; }
    .brand { padding:0 12px 20px; border-bottom:1px solid #ffffff2b; }
    .brand small,.eyebrow { display:block; color:var(--orange); font-size:.72rem; font-weight:900; letter-spacing:.14em; text-transform:uppercase; }
    .brand h1 { margin:5px 0; font-family:"Palatino Linotype",Georgia,serif; font-size:2rem; letter-spacing:-.07em; }
    .brand p { margin:0; color:#b5c9bf; font-size:.85rem; line-height:1.4; }
    nav { display:grid; gap:4px; margin-top:18px; }
    .nav-button { display:flex; gap:11px; width:100%; border:0; border-radius:11px; padding:10px 11px; color:#cce0d5; background:transparent; text-align:left; }
    .nav-button:hover,.nav-button.active { color:#17302b; background:var(--lime); }
    .nav-number { display:grid; place-items:center; width:24px; height:24px; border-radius:50%; color:inherit; background:#ffffff17; font-size:.69rem; font-weight:900; }
    .nav-button.active .nav-number { background:#17302b; color:var(--lime); }
    .nav-button strong { display:block; font-size:.84rem; }
    .nav-button span:last-child { display:block; margin-top:2px; font-size:.7rem; opacity:.74; }
    .key-status { margin:20px 5px 0; border:1px solid #ffffff25; border-radius:12px; padding:11px; color:#bfd6c9; font-size:.75rem; line-height:1.45; }
    .key-status b { color:var(--lime); }
    .reset-key { margin-top:8px; border:0; padding:0; color:#fff; background:none; text-decoration:underline; }
    main { width:min(1080px,100%); margin:0 auto; padding:34px clamp(18px,4vw,56px); }
    .topline { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; margin-bottom:26px; }
    .topline h2 { max-width:700px; margin:5px 0 8px; font-family:"Palatino Linotype",Georgia,serif; font-size:clamp(2rem,4.5vw,3.9rem); letter-spacing:-.065em; line-height:.96; }
    .topline p { max-width:650px; margin:0; color:var(--muted); line-height:1.5; }
    .badge { flex:0 0 auto; border:1px solid var(--ink); border-radius:999px; padding:8px 11px; font-size:.74rem; font-weight:900; }
    .workspace { overflow:hidden; border:1px solid var(--line); border-radius:24px; background:var(--panel); box-shadow:0 20px 50px #17302b12; }
    .workspace-head { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:17px 22px; border-bottom:1px solid var(--line); background:#f9f6ef; }
    .workspace-head strong { font-size:.9rem; }
    .privacy { color:var(--leaf); font-size:.73rem; font-weight:800; }
    #tool-form { display:grid; gap:14px; padding:22px; }
    label { display:grid; gap:7px; color:#42534c; font-size:.82rem; font-weight:900; }
    textarea,input,select { width:100%; border:1px solid var(--line); border-radius:12px; padding:12px 13px; color:var(--ink); background:white; outline:none; }
    textarea { min-height:158px; resize:vertical; line-height:1.5; }
    textarea:focus,input:focus,select:focus { border-color:var(--leaf); box-shadow:0 0 0 3px #d6ef9b88; }
    .fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:13px; }
    .fields.single { grid-template-columns:1fr; }
    .submit { justify-self:start; border:0; border-radius:999px; padding:12px 17px; color:#fff; background:var(--leaf); font-weight:900; box-shadow:0 6px 0 #124232; }
    .submit:hover { transform:translateY(-1px); box-shadow:0 7px 0 #124232; }
    .submit:disabled { cursor:wait; opacity:.65; transform:none; }
    #output { display:grid; gap:14px; margin:0; padding:22px; border-top:1px solid var(--line); background:#fcfaf5; }
    .empty { margin:0; color:var(--muted); font-size:.9rem; }
    .result { border:1px solid var(--line); border-radius:15px; padding:15px; background:white; }
    .result.user { margin-left:12%; border-color:#bddb8b; background:#f4f9e7; }
    .result h3 { margin:0 0 9px; font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; }
    .result p,.result pre { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; color:#35443e; line-height:1.55; font:inherit; }
    .rich-text { display:grid; gap:.65rem; color:#35443e; line-height:1.55; }
    .rich-text p { margin:0; overflow-wrap:anywhere; }
    .rich-text h4 { margin:.35rem 0 0; color:var(--leaf); font-size:.9rem; }
    .rich-text ul { display:grid; gap:.28rem; margin:0; padding-left:1.25rem; }
    .json-entry { display:grid; gap:.25rem; padding:.7rem .8rem; border-left:3px solid var(--lime); background:#f7faed; }
    .json-entry strong { color:var(--leaf); font-size:.78rem; text-transform:uppercase; letter-spacing:.07em; }
    .score { display:inline-grid; place-items:center; width:54px; height:54px; margin-right:12px; border-radius:50%; color:#17302b; background:var(--lime); font-size:1.1rem; font-weight:950; }
    .corrections { margin:10px 0 0; padding-left:20px; color:#42534c; line-height:1.55; }
    .result img { display:block; width:min(100%,560px); border-radius:12px; }
    .result audio { width:min(100%,460px); }
    .loading { color:var(--leaf); font-size:.85rem; font-weight:900; }
    dialog { width:min(510px,calc(100% - 32px)); border:0; border-radius:23px; padding:0; color:var(--ink); background:var(--panel); box-shadow:0 30px 80px #12261ecc; }
    dialog::backdrop { background:#17302bba; backdrop-filter:blur(4px); }
    .key-card { padding:28px; }
    .key-card h2 { margin:8px 0; font-family:"Palatino Linotype",Georgia,serif; font-size:2.2rem; letter-spacing:-.05em; }
    .key-card p { color:var(--muted); line-height:1.55; }
    .key-warning { border-left:4px solid var(--orange); padding:9px 11px; color:#624130; background:#fff0e8; font-size:.82rem; line-height:1.45; }
    .key-card form { display:grid; gap:13px; margin-top:20px; }
    .key-card button { border:0; border-radius:999px; padding:12px 17px; color:#17302b; background:var(--lime); font-weight:950; }
    @media (max-width:800px) { .shell { grid-template-columns:1fr; } aside { padding:15px; } .brand { display:flex; align-items:center; gap:15px; padding-bottom:12px; } .brand p { display:none; } nav { grid-template-columns:repeat(2,minmax(0,1fr)); } .nav-button { min-height:54px; } .topline { display:block; } .badge { display:inline-block; margin-top:14px; } main { padding-top:25px; } }
    @media (max-width:540px) { nav { grid-template-columns:1fr; } .fields { grid-template-columns:1fr; } .topline h2 { font-size:2.6rem; } .result.user { margin-left:0; } }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <header class="brand"><div><small>FastAPI + OpenAI</small><h1>OpenAI Lab.</h1></div><p>Todos los modulos del proyecto de referencia, sin React ni una clave guardada.</p></header>
      <nav id="tool-nav" aria-label="Modulos de IA"></nav>
      <div class="key-status"><b>Modo practica activo</b><br>La clave existe solo mientras esta pestana sigue abierta.<br><button class="reset-key" id="reset-key" type="button">Cambiar clave</button></div>
    </aside>
    <main>
      <header class="topline"><div><span class="eyebrow" id="tool-eyebrow">Modulo 01</span><h2 id="tool-title"></h2><p id="tool-description"></p></div><span class="badge">FastAPI sirve todo</span></header>
      <section class="workspace">
        <header class="workspace-head"><strong id="form-title">Enviar consulta</strong><span class="privacy">La clave no se almacena</span></header>
        <form id="tool-form"></form>
        <section id="output" aria-live="polite"><p class="empty">El resultado aparecera aqui.</p></section>
      </section>
    </main>
  </div>

  <dialog id="key-dialog" open>
    <div class="key-card">
      <span class="eyebrow">Antes de empezar</span>
      <h2>Conecta tu clave.</h2>
      <p>Usa una clave de prueba autorizada para tu grupo. Esta app la envia a FastAPI en cada solicitud y no la guarda.</p>
      <div class="key-warning">Solo para laboratorio local o HTTPS. No publiques esta pantalla ni reutilices una clave personal en una web publica.</div>
      <form id="key-form"><label>Clave de OpenAI<input id="key-input" type="password" autocomplete="off" spellcheck="false" placeholder="sk-..." required autofocus></label><button>Entrar al laboratorio</button></form>
    </div>
  </dialog>

  <script>
    const modules = [
      { id:"orthography", title:"Ortografia", short:"Corregir texto", description:"Detecta mejoras ortograficas y gramaticales en espanol.", endpoint:"/api/orthography", type:"orthography", prompt:"Escribe el texto que quieres corregir" },
      { id:"pros-cons", title:"Pros y contras", short:"Analisis equilibrado", description:"Compara una propuesta con beneficios, riesgos y recomendacion.", endpoint:"/api/pros-cons", type:"text", prompt:"Describe una idea, decision o proyecto" },
      { id:"pros-cons-stream", title:"Analisis en vivo", short:"Respuesta por stream", description:"Muestra el analisis mientras OpenAI genera cada parte.", endpoint:"/api/pros-cons-stream", type:"stream", prompt:"Describe una idea para analizar en vivo" },
      { id:"translate", title:"Traducir", short:"Texto a idiomas", description:"Traduce sin perder el tono ni los nombres propios.", endpoint:"/api/translate", type:"translate", prompt:"Texto que deseas traducir" },
      { id:"text-to-audio", title:"Texto a audio", short:"Voz sintetizada", description:"Convierte un texto en un archivo de audio reproducible.", endpoint:"/api/text-to-audio", type:"audio", prompt:"Texto que quieres escuchar" },
      { id:"audio-to-text", title:"Audio a texto", short:"Transcripcion", description:"Sube un audio breve para obtener su transcripcion.", endpoint:"/api/audio-to-text", type:"audio-file", prompt:"Instruccion opcional para la transcripcion" },
      { id:"image-generation", title:"Generar imagen", short:"Imagen desde prompt", description:"Crea una imagen con el modelo de imagen actual.", endpoint:"/api/image-generation", type:"image", prompt:"Describe la imagen que quieres crear" },
      { id:"image-edit", title:"Editar imagen", short:"Variacion o mascara", description:"Enviale una imagen y una instruccion para modificarla.", endpoint:"/api/image-edit", type:"image-edit", prompt:"Describe exactamente el cambio que quieres" },
      { id:"image-to-text", title:"Leer una imagen", short:"Vision y OCR", description:"Analiza una imagen, describe su contenido o extrae texto.", endpoint:"/api/image-to-text", type:"image-file", prompt:"Pregunta opcional sobre la imagen" },
      { id:"assistant", title:"Asistente", short:"Chat con memoria", description:"Un chat breve. El historial se conserva solo en esta pestana.", endpoint:"/api/assistant", type:"assistant", prompt:"Escribe tu pregunta" }
    ];
    let apiKey = "";
    let active = modules[0];
    let assistantHistory = [];
    const nav = document.querySelector("#tool-nav");
    const form = document.querySelector("#tool-form");
    const output = document.querySelector("#output");
    const keyDialog = document.querySelector("#key-dialog");

    function element(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }
    function setOutputEmpty() {
      output.replaceChildren(element("p", "empty", "El resultado aparecera aqui."));
    }
    function clearEmpty() {
      const empty = output.querySelector(".empty");
      if (empty) empty.remove();
    }
    function appendInline(target, value) {
      String(value).split(/(\*\*[^*]+\*\*)/g).forEach(function(part) {
        if (part.startsWith("**") && part.endsWith("**")) {
          target.append(element("strong", "", part.slice(2, -2)));
        } else {
          target.append(document.createTextNode(part));
        }
      });
    }
    function parseStructuredText(value) {
      const fence = String.fromCharCode(96).repeat(3);
      const start = new RegExp("^" + fence + "(?:json)?\\s*", "i");
      const end = new RegExp("\\s*" + fence + "$");
      const cleaned = String(value).trim().replace(start, "").replace(end, "");
      try {
        const parsed = JSON.parse(cleaned);
        return parsed && typeof parsed === "object" ? parsed : null;
      } catch (error) {
        return null;
      }
    }
    function renderStructuredValue(target, value) {
      if (Array.isArray(value)) {
        const list = element("ul");
        value.forEach(function(item) {
          const row = element("li");
          appendInline(row, typeof item === "object" ? JSON.stringify(item) : item);
          list.append(row);
        });
        target.append(list);
      } else if (value && typeof value === "object") {
        Object.entries(value).forEach(function(entry) {
          const nested = element("div", "json-entry");
          nested.append(element("strong", "", entry[0]));
          renderStructuredValue(nested, entry[1]);
          target.append(nested);
        });
      } else {
        const paragraph = element("p");
        appendInline(paragraph, value);
        target.append(paragraph);
      }
    }
    function renderRichText(target, value) {
      target.replaceChildren();
      const structured = parseStructuredText(value);
      if (structured) {
        Object.entries(structured).forEach(function(entry) {
          const row = element("div", "json-entry");
          row.append(element("strong", "", entry[0]));
          renderStructuredValue(row, entry[1]);
          target.append(row);
        });
        return;
      }
      let list = null;
      String(value).replace(/\r/g, "").split("\n").forEach(function(line) {
        const title = line.match(/^(?:#{1,3}\s+|\*\*)(.+?)(?:\*\*)?:?\s*$/);
        const bullet = line.match(/^\s*[-*]\s+(.+)$/);
        if (!line.trim()) {
          list = null;
        } else if (title) {
          const heading = element("h4");
          appendInline(heading, title[1]);
          target.append(heading);
          list = null;
        } else if (bullet) {
          if (!list) {
            list = element("ul");
            target.append(list);
          }
          const item = element("li");
          appendInline(item, bullet[1]);
          list.append(item);
        } else {
          const paragraph = element("p");
          appendInline(paragraph, line);
          target.append(paragraph);
          list = null;
        }
      });
    }
    function addResult(title, text, user) {
      clearEmpty();
      const card = element("article", "result" + (user ? " user" : ""));
      card.append(element("h3", "", title));
      const content = element("div", "rich-text");
      renderRichText(content, text);
      card.append(content);
      output.append(card);
      card.scrollIntoView({ block:"nearest", behavior:"smooth" });
      return card;
    }
    function addLoading() {
      clearEmpty();
      const loading = element("p", "loading", "Procesando con OpenAI...");
      output.append(loading);
      return loading;
    }
    function renderNav() {
      nav.replaceChildren();
      modules.forEach(function(item, index) {
        const button = element("button", "nav-button" + (item.id === active.id ? " active" : ""));
        button.type = "button";
        button.append(element("span", "nav-number", String(index + 1).padStart(2, "0")));
        const info = element("span");
        info.append(element("strong", "", item.title));
        info.append(element("span", "", item.short));
        button.append(info);
        button.addEventListener("click", function() { active = item; assistantHistory = []; render(); });
        nav.append(button);
      });
    }
    function promptField() {
      const label = element("label", "", active.prompt);
      const textarea = document.createElement("textarea");
      textarea.name = "prompt";
      textarea.required = active.type !== "audio-file" && active.type !== "image-file";
      textarea.placeholder = "Escribe aqui...";
      label.append(textarea);
      return label;
    }
    function addSelect(name, labelText, choices) {
      const label = element("label", "", labelText);
      const select = document.createElement("select");
      select.name = name;
      choices.forEach(function(choice) {
        const option = document.createElement("option");
        option.value = choice.value;
        option.textContent = choice.label;
        select.append(option);
      });
      label.append(select);
      return label;
    }
    function isSupportedImageFile(file) {
      if (!file || !file.name || file.size === 0) return false;
      return ["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(file.type.toLowerCase()) || /\.(jpe?g|png|webp)$/i.test(file.name);
    }
    function imageFileError() {
      return "Selecciona una imagen JPG, PNG o WebP de hasta 10 MB.";
    }
    function addFile(name, labelText, accept, required) {
      const label = element("label", "", labelText);
      const input = document.createElement("input");
      input.type = "file";
      input.name = name;
      input.accept = name === "image" || name === "mask" ? "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" : accept;
      input.required = required;
      if (name === "image" || name === "mask") {
        input.addEventListener("change", function() {
          const file = input.files[0];
          input.setCustomValidity(!file || isSupportedImageFile(file) ? "" : imageFileError());
        });
      }
      label.append(input);
      return label;
    }
    function render() {
      renderNav();
      document.querySelector("#tool-eyebrow").textContent = "Modulo " + String(modules.indexOf(active) + 1).padStart(2, "0");
      document.querySelector("#tool-title").textContent = active.title + ".";
      document.querySelector("#tool-description").textContent = active.description;
      document.querySelector("#form-title").textContent = active.type === "assistant" ? "Conversacion" : "Nueva solicitud";
      form.replaceChildren();
      const fields = element("div", "fields single");
      if (active.type === "image-edit") {
        fields.className = "fields";
        fields.append(promptField(), addFile("image", "Imagen original (maximo 10 MB)", "image/*", true), addFile("mask", "Mascara opcional", "image/*", false));
      } else if (active.type === "image-file") {
        fields.className = "fields";
        fields.append(promptField(), addFile("image", "Imagen (maximo 10 MB)", "image/*", true));
      } else if (active.type === "audio-file") {
        fields.className = "fields";
        fields.append(promptField(), addFile("file", "Audio (maximo 10 MB)", "audio/*", true));
      } else {
        fields.append(promptField());
        if (active.type === "translate") fields.append(addSelect("target_language", "Idioma de destino", [{value:"ingles",label:"Ingles"},{value:"portugues",label:"Portugues"},{value:"frances",label:"Frances"},{value:"quechua",label:"Quechua"}]));
        if (active.type === "audio") fields.append(addSelect("voice", "Voz", [{value:"alloy",label:"Alloy"},{value:"nova",label:"Nova"},{value:"sage",label:"Sage"},{value:"coral",label:"Coral"}]));
      }
      form.append(fields);
      const submit = element("button", "submit", active.type === "stream" ? "Analizar en vivo" : active.type === "assistant" ? "Enviar mensaje" : "Procesar");
      submit.type = "submit";
      form.append(submit);
      setOutputEmpty();
    }
    async function request(url, options) {
      const headers = new Headers(options && options.headers ? options.headers : {});
      headers.set("X-OpenAI-Key", apiKey);
      const response = await fetch(url, Object.assign({}, options || {}, { headers:headers }));
      if (!response.ok) {
        let detail = "No se pudo completar la solicitud.";
        try { detail = (await response.json()).detail || detail; } catch (error) {}
        throw new Error(detail);
      }
      return response;
    }
    async function streamResponse(prompt) {
      const response = await request(active.endpoint, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({prompt:prompt}) });
      const card = addResult("Respuesta en vivo", "");
      const content = card.querySelector(".rich-text");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        text += decoder.decode(part.value, {stream:true});
        renderRichText(content, text);
      }
      text += decoder.decode();
      renderRichText(content, text);
    }
    function showOrthography(data) {
      const card = element("article", "result");
      card.append(element("h3", "", "Revision"));
      const row = document.createElement("div");
      row.append(element("span", "score", String(data.score || 0) + "%"));
      const message = element("div", "rich-text");
      renderRichText(message, data.message || "Revision completada.");
      row.append(message);
      card.append(row);
      if (Array.isArray(data.corrections) && data.corrections.length) {
        const list = element("ul", "corrections");
        data.corrections.forEach(function(correction) { list.append(element("li", "", correction)); });
        card.append(list);
      }
      output.append(card);
    }
    function showImage(data) {
      const card = element("article", "result");
      card.append(element("h3", "", "Imagen generada"));
      const image = document.createElement("img");
      image.src = data.image_url;
      image.alt = data.revised_prompt || "Imagen generada por OpenAI";
      card.append(image);
      if (data.revised_prompt) card.append(element("p", "", "Prompt ajustado: " + data.revised_prompt));
      output.append(card);
    }
    async function execute(event) {
      event.preventDefault();
      const submit = form.querySelector(".submit");
      const data = new FormData(form);
      const prompt = String(data.get("prompt") || "").trim();
      if (!apiKey) { keyDialog.showModal(); return; }
      if (active.type !== "audio-file" && active.type !== "image-file" && !prompt) return;
      if ((active.type === "image-file" || active.type === "image-edit") && !isSupportedImageFile(data.get("image"))) {
        addResult("Error", imageFileError());
        return;
      }
      if (active.type === "image-edit") {
        const mask = data.get("mask");
        if (mask && mask.size && !isSupportedImageFile(mask)) {
          addResult("Error", "La mascara debe ser una imagen JPG, PNG o WebP de hasta 10 MB.");
          return;
        }
      }
      submit.disabled = true;
      setOutputEmpty();
      try {
        if (active.type === "assistant") {
          addResult("Tu", prompt, true);
          const response = await request(active.endpoint, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:prompt,history:assistantHistory.slice(-12)})});
          const result = await response.json();
          assistantHistory.push({role:"user",content:prompt},{role:"assistant",content:result.text});
          addResult("Asistente", result.text);
        } else if (active.type === "stream") {
          await streamResponse(prompt);
        } else if (active.type === "audio-file" || active.type === "image-file" || active.type === "image-edit") {
          const loading = addLoading();
          const response = await request(active.endpoint, {method:"POST",body:data});
          const result = await response.json();
          loading.remove();
          if (active.type === "image-edit") showImage(result); else addResult("Resultado", result.text);
        } else if (active.type === "audio") {
          const loading = addLoading();
          const response = await request(active.endpoint, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:prompt,voice:data.get("voice")})});
          const audio = await response.blob();
          loading.remove();
          const card = element("article", "result");
          card.append(element("h3", "", "Audio listo"));
          const player = document.createElement("audio");
          player.controls = true;
          player.src = URL.createObjectURL(audio);
          card.append(player);
          output.append(card);
        } else if (active.type === "image") {
          const loading = addLoading();
          const response = await request(active.endpoint, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:prompt})});
          const result = await response.json();
          loading.remove();
          showImage(result);
        } else {
          addResult("Tu", prompt, true);
          const payload = {prompt:prompt};
          if (active.type === "translate") payload.target_language = data.get("target_language");
          const loading = addLoading();
          const response = await request(active.endpoint, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
          const result = await response.json();
          loading.remove();
          if (active.type === "orthography") showOrthography(result); else addResult("Resultado", result.text);
        }
      } catch (error) {
        addResult("Error", error.message || "No se pudo completar la solicitud.");
      } finally {
        submit.disabled = false;
      }
    }
    document.querySelector("#key-form").addEventListener("submit", function(event) {
      event.preventDefault();
      apiKey = document.querySelector("#key-input").value.trim();
      if (apiKey) keyDialog.close();
    });
    document.querySelector("#reset-key").addEventListener("click", function() {
      apiKey = "";
      document.querySelector("#key-input").value = "";
      keyDialog.showModal();
    });
    form.addEventListener("submit", execute);
    render();
  </script>
</body>
</html>
```
:::

::: details requirements.txt — dependencias
```text
fastapi==0.116.1
uvicorn[standard]>=0.30.0
openai>=2.33.0
python-multipart>=0.0.20
```
:::

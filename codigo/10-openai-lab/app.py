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

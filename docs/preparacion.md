# Instaladores y preparación

Para las prácticas se necesita **Python, VS Code, Git y un navegador moderno**. No hace falta instalar herramientas adicionales de servidor durante el laboratorio.

## Descargas obligatorias

<div class="download-grid">
  <a class="download-card" href="https://www.python.org/downloads/windows/" target="_blank" rel="noopener"><small>PASO 1</small><strong>Python para Windows</strong><span>Descarga la versión de 64 bits y activa “Add Python to PATH”.</span></a>
  <a class="download-card" href="https://code.visualstudio.com/Download" target="_blank" rel="noopener"><small>PASO 2</small><strong>Visual Studio Code</strong><span>Editor para abrir, ejecutar y modificar los proyectos.</span></a>
  <a class="download-card" href="https://git-scm.com/download/win" target="_blank" rel="noopener"><small>PASO 3</small><strong>Git para Windows</strong><span>Recomendado para trabajar con versiones y para Claude Code.</span></a>
  <a class="download-card featured" href="./downloads/curso-completo.zip" download><small>PASO 4</small><strong>Código completo</strong><span>Diez demos con backend, frontend e instrucciones.</span></a>
</div>

## Asistente de IA — elige uno

### Opción A: Codex para VS Code

1. Instala [Codex – OpenAI's coding agent](https://marketplace.visualstudio.com/items?itemName=openai.chatgpt).
2. Abre el panel de Codex en VS Code.
3. Inicia sesión o configura la clave API autorizada para tu grupo.
4. Si la clave es restringida, debe permitir **Responses → Write**.

Una clave sin ese permiso produce el error:

```text
401 Missing scopes: api.responses.write
```

[Guía de Codex para IDE](https://developers.openai.com/codex/ide) · [Autenticación de Codex](https://developers.openai.com/codex/auth)

### Opción B: Claude Code con API key

::: warning No instalar Claude Desktop para esta modalidad
Claude Desktop muestra una pantalla de inicio con Google o correo. Esa aplicación no ofrece un campo para pegar una API key. Para la clase se debe instalar **Claude Code**.
:::

#### 1. Instalar Claude Code

Abre **PowerShell** y ejecuta una de estas opciones:

```powershell
winget install Anthropic.ClaudeCode
```

Si `winget` no está disponible, utiliza el instalador nativo oficial:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Cierra PowerShell, vuelve a abrirlo y verifica:

```powershell
claude --version
```

#### 2. Cargar la clave temporal del grupo

En la misma ventana de PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-CLAVE-DEL-GRUPO"
```

La clave desaparece al cerrar esa terminal. No debe guardarse dentro del proyecto.

#### 3. Abrir el proyecto

```powershell
cd C:\ruta\del\proyecto
claude
```

Claude Code detectará la variable y pedirá aprobar la clave. Con esta modalidad **no es necesario usar `/login`**.

#### 4. Usarlo como panel de VS Code

1. Instala la extensión oficial [Claude Code](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code).
2. Cierra todas las ventanas de VS Code.
3. En el PowerShell donde cargaste la clave, ejecuta:

```powershell
code .
```

Así VS Code hereda `ANTHROPIC_API_KEY`. Dentro de Claude Code puedes ejecutar `/status` para confirmar que la autenticación activa corresponde a la API.

[Instalación oficial de Claude Code](https://code.claude.com/docs/en/setup) · [Integración con VS Code](https://code.claude.com/docs/en/vs-code)

::: warning Protege las claves
Nunca las pegues en `app.py`, `.env` compartidos, capturas, repositorios o chats. Usa una clave diferente por grupo y revócala al finalizar la clase.
:::

## Resumen de instalación

| Componente | Obligatorio | Uso en el taller |
|---|:---:|---|
| Python 3.11 o superior | Sí | Ejecutar FastAPI y los WebSockets. |
| Visual Studio Code | Sí | Editar y ejecutar el código. |
| Git para Windows | Recomendado | Versionar cambios y facilitar Claude Code. |
| Codex o Claude Code | Uno de los dos | Comprender, modificar y revisar el proyecto. |
| Navegador moderno | Sí | Abrir varios clientes simultáneos. |

## Herramientas que no instalaremos

| Herramienta | Decisión para estas cuatro horas |
|---|---|
| Docker | No se usa; quitaría tiempo a los ejercicios. |
| Postman | No es necesario; la interfaz web prueba el WebSocket. |
| Node.js | Opcional; solo se necesita para modificar este sitio VuePress. |
| Claude Desktop | No se usa con las claves API de los grupos. |

## Verificar el equipo

Abre PowerShell o la terminal de VS Code:

```powershell
python --version
git --version
code --version
claude --version
```

Si Windows no reconoce `python`, prueba `py --version` y sustituye `python` por `py` en los comandos del curso.

## Ejecutar cualquier proyecto

Después de descargar y descomprimir el curso:

```powershell
cd codigo\01-websocket-base
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000). Para cambiar de demo, detén el servidor con `Ctrl + C` y repite el proceso dentro de otra carpeta.

### Probar desde otras computadoras

Si todos están en la misma red Wi-Fi, quien ejecute el servidor usa:

```powershell
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
ipconfig
```

Busca la **Dirección IPv4** de ese equipo. Los participantes abren `http://DIRECCION-IP:8000`; por ejemplo, `http://192.168.1.25:8000`. Si Windows pregunta, permite el acceso solamente en redes privadas.

::: details Si PowerShell bloquea la activación
Ejecuta esto únicamente en la terminal actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```
:::

## Lista de comprobación

- Python muestra su versión.
- El navegador abre `127.0.0.1:8000`.
- Dos pestañas pueden enviarse eventos.
- Codex o Claude Code puede leer la carpeta del proyecto.

[Continuar con Python esencial →](/python-esencial.html)

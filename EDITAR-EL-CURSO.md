# Cómo editar el curso

Este ZIP contiene el proyecto VuePress completo y los ejercicios de Python/FastAPI.

## Carpetas importantes

- `docs/`: páginas del curso en Markdown.
- `docs/python-esencial.md`: introducción práctica a la sintaxis de Python usada en las demos.
- `docs/laboratorio-websocket.md`: explicación breve y laboratorio común de WebSocket.
- `docs/preparacion.md`: instaladores y configuración de Codex o Claude Code.
- `docs/.vuepress/config.js`: menú y navegación.
- `docs/.vuepress/styles/index.scss`: diseño del sitio.
- `codigo/`: proyectos completos de FastAPI y WebSocket.
- `scripts/generate-code-pages.mjs`: genera las páginas que muestran todo el código.
- `docs/.vuepress/public/vuepress-logo.png`: logo de VuePress usado en la navegación.
- `docs/.vuepress/public/vuepress-hero.png`: ilustración de VuePress usada en la portada.

## Abrir el sitio localmente

Instala Node.js LTS y abre una terminal en esta carpeta:

```powershell
npm install
npm run docs:dev
```

VuePress mostrará una dirección local, normalmente `http://localhost:8080`.

## Editar una página

Por ejemplo, para cambiar el plan de clase edita `docs/plan.md`. Para modificar una demo edita su `app.py` o `static/index.html` dentro de `codigo/`.

Después de cambiar el código de una demo ejecuta:

```powershell
npm run course:sync
```

Esto vuelve a generar las páginas de código visible. Para construir la versión final:

```powershell
npm run build
```

## Guardarlo en tu GitHub

El repositorio público del proyecto es:

https://github.com/waready/curso-taller-2026

Para publicar nuevos cambios:

```powershell
git add .
git commit -m "Curso FastAPI y WebSocket"
git push -u origin main
```

No subas claves de OpenAI, Anthropic ni archivos `.env`.

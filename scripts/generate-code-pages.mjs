import { cp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const root = process.cwd();
const codeRoot = join(root, 'codigo');
const docsRoot = join(root, 'docs', 'codigo');
const publicSource = join(root, 'docs', '.vuepress', 'public', 'source');
const repositoryUrl = 'https://github.com/waready/curso-taller-2026';

const titles = {
  '01-websocket-base': 'WebSocket Base',
  '02-chat-tiempo-real': 'Chat con presencia',
  '03-wplace-colaborativo': 'Mini-WPlace colaborativo',
  '04-reacciones-en-vivo': 'Reacciones en vivo',
  '05-encuesta-battle': 'Encuesta Battle',
  '06-cursor-party': 'Cursor Party',
  '07-tracker-delivery': 'Tracker Delivery Puno',
  '08-subasta-flash': 'Subasta Flash',
  '09-cartas-casino': 'Cartas Casino',
  '10-openai-lab': 'OpenAI Lab con FastAPI',
};

const folders = (await readdir(codeRoot, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory() && titles[entry.name])
  .map((entry) => entry.name)
  .sort();

await rm(publicSource, { recursive: true, force: true });
await mkdir(publicSource, { recursive: true });
await cp(codeRoot, publicSource, {
  recursive: true,
  filter: (source) => !source.includes('__pycache__') && !source.includes('.venv'),
});
await mkdir(docsRoot, { recursive: true });

const escapeFence = (value) => value.replaceAll('````', '``` `');

for (const folder of folders) {
  const project = join(codeRoot, folder);
  const app = await readFile(join(project, 'app.py'), 'utf8');
  const html = await readFile(join(project, 'static', 'index.html'), 'utf8');
  const requirements = await readFile(join(project, 'requirements.txt'), 'utf8');
  const readme = await readFile(join(project, 'README.md'), 'utf8');
  const readmeBody = readme.replace(/^# .+\r?\n+/, '').trimStart();

  const page = `# ${titles[folder]} — código completo

[Ver proyecto completo en GitHub](${repositoryUrl}/tree/main/codigo/${folder}) · [Descargar ZIP](/downloads/${folder}.zip) · [Abrir app.py](/source/${folder}/app.py) · [Abrir index.html](/source/${folder}/static/index.html)

${readmeBody}

## Ejecutar

\`\`\`powershell
cd codigo\\${folder}
python -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
\`\`\`

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000).

::: details app.py — backend completo
\`\`\`python
${escapeFence(app).trimEnd()}
\`\`\`
:::

::: details static/index.html — frontend completo
\`\`\`html
${escapeFence(html).trimEnd()}
\`\`\`
:::

::: details requirements.txt — dependencias
\`\`\`text
${escapeFence(requirements).trimEnd()}
\`\`\`
:::
`;

  await writeFile(join(docsRoot, `${folder}.md`), page, 'utf8');
}

const cards = folders
  .map((folder) => `  <a class="project-card" href="./${folder}.html"><strong>${titles[folder]}</strong><span>Backend, frontend, dependencias, ejecución y ZIP.</span></a>`)
  .join('\n');

const index = `# Código completo de la clase

Aquí no hay fragmentos incompletos: cada proyecto muestra **todo el backend y todo el frontend**, permite abrir los archivos originales y ofrece un ZIP independiente.

[Ver todos los códigos en GitHub](${repositoryUrl}/tree/main/codigo) · [Descargar los diez proyectos](/downloads/curso-completo.zip) · [Descargar la fuente editable v8](/downloads/curso-arquitecturas-v8-editable.zip)

Abre cada proyecto y despliega **app.py** o **static/index.html**. Todos los bloques tienen el botón **Copiar**.

<div class="project-grid">
${cards}
</div>

## Misma forma de ejecución

Todos los proyectos incluyen únicamente dos dependencias: FastAPI y Uvicorn. Entra a la carpeta elegida, instala \`requirements.txt\` y ejecuta \`python -m uvicorn app:app --reload\`.
`;

await writeFile(join(docsRoot, 'README.md'), index, 'utf8');
console.log(`Generadas ${folders.length} páginas de código y archivos fuente públicos.`);

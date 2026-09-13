import { viteBundler } from '@vuepress/bundler-vite'
import { defaultTheme } from '@vuepress/theme-default'
import { defineUserConfig } from 'vuepress'

const base = process.env.DOCS_BASE || '/'

export default defineUserConfig({
  lang: 'es-PE',
  base,
  title: 'Curso Taller 2026',
  description: 'Arquitecturas Distribuidas y Desarrollo Asistido por Inteligencia Artificial con Python y FastAPI',
  dest: 'build',
  bundler: viteBundler({
    viteOptions: {
      server: {
        host: '0.0.0.0',
        strictPort: true,
        allowedHosts: ['terminal.local'],
      },
    },
  }),
  head: [
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { name: 'color-scheme', content: 'dark light' }],
    ['link', { rel: 'icon', type: 'image/png', href: `${base}vuepress-logo.png` }],
  ],
  theme: defaultTheme({
    logo: '/vuepress-logo.png',
    logoAlt: 'VuePress',
    navbar: [
      { text: 'Inicio', link: '/' },
      { text: 'Instaladores', link: '/preparacion.html' },
      { text: 'Python esencial', link: '/python-esencial.html' },
      { text: 'WebSocket esencial', link: '/laboratorio-websocket.html' },
      { text: 'Prompts de IA', link: '/ia.html' },
      { text: 'Demos y ejercicios', link: '/proyectos/' },
      { text: 'Código', link: '/codigo/' },
    ],
    sidebar: {
      '/proyectos/': [
        {
          text: 'Proyectos por grupos',
          children: [
            '/proyectos/README.md',
            '/proyectos/websocket-base.md',
            '/proyectos/chat.md',
            '/proyectos/wplace.md',
            '/proyectos/reacciones.md',
            '/proyectos/encuesta.md',
            '/proyectos/cursor-party.md',
            '/proyectos/tracker.md',
            '/proyectos/subasta.md',
            '/proyectos/cartas.md',
            '/proyectos/openai-lab.md',
          ],
        },
      ],
      '/codigo/': [
        {
          text: 'Código completo',
          children: [
            '/codigo/README.md',
            '/codigo/01-websocket-base.md',
            '/codigo/02-chat-tiempo-real.md',
            '/codigo/03-wplace-colaborativo.md',
            '/codigo/04-reacciones-en-vivo.md',
            '/codigo/05-encuesta-battle.md',
            '/codigo/06-cursor-party.md',
            '/codigo/07-tracker-delivery.md',
            '/codigo/08-subasta-flash.md',
            '/codigo/09-cartas-casino.md',
            '/codigo/10-openai-lab.md',
          ],
        },
      ],
      '/': [
        {
          text: 'Taller de 4 horas',
          children: [
            '/preparacion.md',
            '/python-esencial.md',
            '/laboratorio-websocket.md',
            '/ia.md',
          ],
        },
      ],
    },
    editLink: false,
    contributors: false,
    lastUpdated: false,
    notFound: ['Esta ruta se desconectó.', 'Aquí no vive ningún WebSocket.'],
    backToHome: 'Volver al inicio',
    toggleColorMode: 'Cambiar tema',
    toggleSidebar: 'Abrir menú',
  }),
})

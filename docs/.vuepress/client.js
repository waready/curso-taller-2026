import { defineClientConfig } from 'vuepress/client'
import { onMounted } from 'vue'

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }

  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.opacity = '0'
  document.body.append(area)
  area.select()
  document.execCommand('copy')
  area.remove()
  return Promise.resolve()
}

function addCopyButtons() {
  document.querySelectorAll('div[class*="language-"]').forEach((block) => {
    if (block.querySelector(':scope > .copy-code-button')) return

    const code = block.querySelector('pre code')
    if (!code) return

    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'copy-code-button'
    button.textContent = 'Copiar'
    button.setAttribute('aria-label', 'Copiar código')
    button.addEventListener('click', async () => {
      await copyText(code.textContent || '')
      button.textContent = 'Copiado ✓'
      window.setTimeout(() => {
        button.textContent = 'Copiar'
      }, 1600)
    })
    block.append(button)
  })
}

function enhanceTables() {
  document.querySelectorAll('#content table').forEach((table) => {
    if (table.parentElement?.classList.contains('table-shell')) return

    const shell = document.createElement('div')
    shell.className = 'table-shell'
    shell.setAttribute('tabindex', '0')
    shell.setAttribute('role', 'region')
    shell.setAttribute('aria-label', 'Tabla desplazable')
    table.before(shell)
    shell.append(table)
  })
}

function enhanceContent() {
  addCopyButtons()
  enhanceTables()
}

export default defineClientConfig({
  setup() {
    onMounted(() => {
      enhanceContent()
      new MutationObserver(enhanceContent).observe(document.body, {
        childList: true,
        subtree: true,
      })
    })
  },
})

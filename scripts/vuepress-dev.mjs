import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const cli = fileURLToPath(new URL('../node_modules/vuepress/bin/vuepress.js', import.meta.url))
const forwardedArgs = process.argv.slice(2).filter((argument) => argument !== '--strictPort')
const result = spawnSync(process.execPath, [cli, 'dev', 'docs', ...forwardedArgs], {
  stdio: 'inherit',
})

process.exit(result.status ?? 1)

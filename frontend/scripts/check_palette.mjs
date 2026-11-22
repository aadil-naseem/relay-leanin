import { readdir, readFile } from 'node:fs/promises'
import { extname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../src/', import.meta.url))
const allowed = new Set(['styles/tokens.css', 'scene/palette.js'])
const extensions = new Set(['.css', '.js', '.jsx', '.svg'])
const literalPattern = /#[\da-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\s*\(/g
const palette = new Set([
  '#000000', '#0A1A40', '#00205B', '#1A3070', '#003087', '#307FE2',
  '#F2A900', '#C8920A', '#E8C870', '#FFE264', '#F8F0DC', '#FFFFFF',
])

async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await filesIn(path))
    else if (extensions.has(extname(entry.name))) files.push(path)
  }
  return files
}

const violations = []
for (const path of await filesIn(root)) {
  const rel = relative(root, path).replaceAll('\\', '/')
  const source = await readFile(path, 'utf8')
  const matches = [...source.matchAll(literalPattern)]
  if (!matches.length) continue
  if (!allowed.has(rel)) {
    for (const match of matches) violations.push(`${rel}: palette literal ${match[0]}`)
  } else if (rel === 'styles/tokens.css') {
    for (const match of source.matchAll(/#[\da-fA-F]{3,8}\b/g)) {
      if (!palette.has(match[0].toUpperCase())) {
        violations.push(`${rel}: unapproved palette value ${match[0]}`)
      }
    }
  }
}

if (violations.length) {
  console.error('Palette literals belong only in styles/tokens.css (and scene/palette.js):')
  for (const violation of violations) console.error(`  ${violation}`)
  process.exitCode = 1
} else {
  console.log('Palette lint passed.')
}

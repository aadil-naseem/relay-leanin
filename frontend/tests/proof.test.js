import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const report = JSON.parse(readFileSync(new URL('../src/data/backtest.json', import.meta.url), 'utf8'))

test('Michaung proof data matches the committed report and ranking separation', () => {
  assert.equal(report.source_report, 'docs/BACKTEST_EXPOSURE.md')
  assert.equal(report.sites.length, 7)
  const flooded = report.sites.filter((site) => site.label === 'FLOODED')
  const notFlooded = report.sites.filter((site) => site.label === 'NOT FLOODED')
  const gap = Math.min(...flooded.map((site) => site.risk))
    - Math.max(...notFlooded.map((site) => site.risk))

  assert.equal(gap, 22)
  assert.equal(gap, report.separation_points)
  assert.ok(flooded.every((site) => site.risk > Math.max(...notFlooded.map((other) => other.risk))))
})

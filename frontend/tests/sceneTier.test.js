import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chooseSceneTier } from '../src/lib/sceneTier.js'
import { chapterAt, localChapterProgress } from '../src/lib/storyProgress.js'

test('scene tier honors static safety fallbacks before requested quality', () => {
  assert.equal(chooseSceneTier({ requested: 'full', webgl: false }), 'static')
  assert.equal(chooseSceneTier({ requested: 'full', mobile: true }), 'static')
  assert.equal(chooseSceneTier({ requested: 'lite', reducedMotion: true }), 'static')
  assert.equal(chooseSceneTier({ requested: 'static', webgl: true }), 'static')
})

test('scene tier honors explicit quality and conservatively resolves auto', () => {
  assert.equal(chooseSceneTier({ requested: 'full', cores: 4 }), 'full')
  assert.equal(chooseSceneTier({ requested: 'lite', cores: 16 }), 'lite')
  assert.equal(chooseSceneTier({ requested: 'auto', cores: 8 }), 'full')
  assert.equal(chooseSceneTier({ requested: 'auto', cores: 4 }), 'lite')
})

test('landing fallback values remain clearly identified as replay sample data', () => {
  const fallback = JSON.parse(readFileSync(new URL('../src/data/story.fallback.json', import.meta.url), 'utf8'))
  assert.equal(fallback.data_label, 'SIMULATED SAMPLE')
  assert.equal(fallback.weather_mode, 'replay')
  assert.equal(fallback.spof.name, 'Sample Heat Treat Works')
  assert.equal(fallback.spof.orders_broken, 2)
  assert.equal(fallback.stress.revenue_exposed_inr, 3_950_000)
  assert.match(fallback.source, /verified replay/)
  assert.equal(fallback.readiness.weighted_score, 53.9)
})

test('scroll story maps progress to five reversible chapter ranges', () => {
  assert.deepEqual([0, 0.1, 0.4, 0.7, 0.9].map(chapterAt), [0, 1, 2, 3, 4])
  assert.equal(chapterAt(1), 4)
  assert.equal(localChapterProgress(0.21, 1), 0.5)
  assert.equal(localChapterProgress(0.42, 1), 1)
})

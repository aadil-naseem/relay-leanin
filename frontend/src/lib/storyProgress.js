export const STORY_CHAPTERS = [
  { start: 0, end: 0.08, label: 'FIND' },
  { start: 0.08, end: 0.34, label: 'DIAGNOSE' },
  { start: 0.34, end: 0.6, label: 'THREAT' },
  { start: 0.6, end: 0.86, label: 'RELAY' },
  { start: 0.86, end: 1, label: 'READY' },
]

export function chapterAt(progress) {
  const p = Math.max(0, Math.min(1, progress))
  return STORY_CHAPTERS.findIndex((chapter, index) =>
    p < chapter.end || index === STORY_CHAPTERS.length - 1)
}

export function localChapterProgress(progress, chapterIndex) {
  const chapter = STORY_CHAPTERS[chapterIndex]
  if (!chapter) return 0
  return Math.max(0, Math.min(1, (progress - chapter.start) / (chapter.end - chapter.start)))
}

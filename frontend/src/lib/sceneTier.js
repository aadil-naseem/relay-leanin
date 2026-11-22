export function chooseSceneTier({
  requested = 'auto',
  mobile = false,
  reducedMotion = false,
  webgl = true,
  cores = 8,
}) {
  if (requested === 'static' || mobile || reducedMotion || !webgl) return 'static'
  if (requested === 'full' || requested === 'lite') return requested
  return cores >= 8 ? 'full' : 'lite'
}

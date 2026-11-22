export function TitleBlock({ sheet = 'SHEET 1/8' }) {
  return (
    <aside className="f0-title-block" aria-label="Drawing title block">
      DWG: RELAY-S2 · REV: DATA SNAPSHOT · SCALE: 1:1 · {sheet} · SAMPLE / SIMULATED
    </aside>
  )
}

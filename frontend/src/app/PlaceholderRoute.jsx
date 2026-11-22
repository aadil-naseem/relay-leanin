import { TitleBlock } from '../components/TitleBlock'

export function PlaceholderRoute({ number, title, route }) {
  return (
    <>
      <main className="f0-content">
        <div className="f0-kicker">FOUNDATION · {number}</div>
        <h1>{title}</h1>
        <p>This route is wired for the RELAY screen build. The screen design will be added one at a time.</p>
        <section className="f0-panel" aria-label="Route information">
          <div className="f0-mono">ROUTE · {route}</div>
          <p>Shared shell and navigation are in place. Screen content will be built one view at a time.</p>
        </section>
      </main>
      <TitleBlock />
    </>
  )
}

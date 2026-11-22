import { Button, Frame, Nameplate, Stamp } from '../../components/primitives'
import { useRelayNavigate } from '../../app/navigation'
import backtest from '../../data/backtest.json'
import './proof.css'

const methods = [
  {
    code: 'M4',
    title: 'Exposure',
    formula: 'H = max(H₂₄, H₃)',
    detail: 'Risk = round(100 × H × [floor + (1 − floor) × V]). V combines local depression, water proximity and curated flood-history zones.',
  },
  {
    code: 'M3',
    title: 'Weak points',
    formula: 'Remove one resource → re-check coverage',
    detail: 'A machine, vendor or supplier is a SPOF if its removal breaks a baseline-covered requirement. Rank by broken-order revenue, then order count.',
  },
  {
    code: 'M6',
    title: 'Matching',
    formula: '100 × (.40 status + .20 time + .15 capacity + .15 freshness + .10 separation)',
    detail: 'Hard filters and correlated-risk exclusions happen first. Only viable, non-excluded candidates enter this ranking.',
  },
  {
    code: 'M8',
    title: 'Readiness',
    formula: '100 × Σ(weight covered) / Σ(weight critical)',
    detail: 'Part weight is open-order value (fallback 1). Coverage requires a capable, READY, fresh and non-correlated partner within the selected window.',
  },
]

const glossary = [
  ['Production Passport', 'Structured part and process information a backup factory can use to assess fit.'],
  ['Redacted RFQ', 'A request containing approved technical fields, with customer-identifying details removed.'],
  ['SPOF', 'A machine, vendor or material whose loss breaks an active order requirement with no alternative.'],
  ['Exposure', 'A risk indicator from forecast rain and site conditions over a time window; not a flood probability.'],
  ['Recovery Readiness Score', 'The value-weighted share of critical production with a viable fallback in the chosen window.'],
  ['Correlated risk', 'Shared hazard-zone, cluster or grid conditions that can make owner and backup fail together.'],
]

export default function Proof() {
  const navigate = useRelayNavigate()
  const flooded = backtest.sites.filter((site) => site.label === 'FLOODED')
  const notFlooded = backtest.sites.filter((site) => site.label === 'NOT FLOODED')
  const observedGap = Math.min(...flooded.map((site) => site.risk))
    - Math.max(...notFlooded.map((site) => site.risk))
  const reportDate = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(backtest.generated_at_utc))

  return (
    <main className="proof-page">
      <header className="proof-heading">
        <div>
          <span className="f0-kicker">S8 · PROOF & METHOD</span>
          <h1>SHOW THE WORK</h1>
          <p>What the score says, what it does not, and where every number comes from.</p>
        </div>
        <Stamp tone="gold">HISTORICAL CHECK · NOT A FORECAST GUARANTEE</Stamp>
      </header>

      <section aria-labelledby="proof-backtest-title">
        <div className="proof-section-heading">
          <div>
            <span className="f0-kicker">M4 · EXPOSURE BACK-TEST</span>
            <h2 id="proof-backtest-title">{backtest.event} · {backtest.region}</h2>
          </div>
          <Nameplate>{backtest.event_period} · REPLAY</Nameplate>
        </div>

        <Frame className="proof-backtest">
          <div className="proof-result">
            <span className="proof-result__value">+{observedGap}<small> pts</small></span>
            <div>
              <strong>Flood-labelled sites rank above the others in this 7-site set.</strong>
              <p>Lowest labelled flooded score {Math.min(...flooded.map((site) => site.risk))} · highest labelled not flooded score {Math.max(...notFlooded.map((site) => site.risk))}</p>
            </div>
            <span className="proof-result__pass"><i aria-hidden="true">✓</i> REPORT PASS</span>
          </div>

          <div className="proof-table-wrap">
            <table className="proof-table">
              <caption>
                Michaung replay ranking · report generated {reportDate} · risk indicator out of 100
              </caption>
              <thead>
                <tr>
                  <th scope="col">Rank</th>
                  <th scope="col">Site</th>
                  <th scope="col">Public-report label</th>
                  <th scope="col">Risk score</th>
                  <th scope="col">Max 24 h rain</th>
                </tr>
              </thead>
              <tbody>
                {backtest.sites.map((site, index) => (
                  <tr key={site.site}>
                    <td className="proof-table__rank">{String(index + 1).padStart(2, '0')}</td>
                    <th scope="row">{site.site}</th>
                    <td>
                      <span className={`proof-truth proof-truth--${site.label === 'FLOODED' ? 'flooded' : 'dry'}`}>
                        <i aria-hidden="true">{site.label === 'FLOODED' ? '●' : '○'}</i>
                        {site.label === 'FLOODED' ? 'Flooded' : 'Not flooded'}
                      </span>
                    </td>
                    <td>
                      <div className="proof-score">
                        <span className="proof-score__track" aria-hidden="true">
                          <i className={site.label === 'FLOODED' ? 'is-flooded' : ''} style={{ width: `${site.risk}%` }} />
                        </span>
                        <b>{site.risk}</b>
                      </div>
                    </td>
                    <td>{site.rain_24h_mm.toFixed(1)} mm</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="proof-legend" aria-label="Chart legend">
            <span><i className="is-flooded" aria-hidden="true" /> Public reports labelled flooded</span>
            <span><i aria-hidden="true" /> Public reports labelled not flooded</span>
          </div>
          <p className="proof-caveat">
            This is the existing M4 report in <code>docs/BACKTEST_EXPOSURE.md</code>, not the deferred Phase 14 integration gate.
            Labels summarize public reporting; this small, curated comparison is not an independent blind validation.
          </p>
        </Frame>
      </section>

      <section aria-labelledby="proof-method-title">
        <div className="proof-section-heading">
          <div>
            <span className="f0-kicker">METHOD · DETERMINISTIC CORE</span>
            <h2 id="proof-method-title">HOW THE NUMBERS ARE MADE</h2>
          </div>
          <span className="proof-section-note">CALCULATION TRACES ARE AVAILABLE IN THE APP</span>
        </div>
        <div className="proof-method-grid">
          {methods.map((method, index) => (
            <Frame className="proof-method" key={method.code}>
              <div className="proof-method__top">
                <span>{String(index + 1).padStart(2, '0')} / {method.code}</span>
                <h3>{method.title}</h3>
              </div>
              <code>{method.formula}</code>
              <p>{method.detail}</p>
            </Frame>
          ))}
        </div>
        <p className="proof-footnote">
          H maps rolling 24-hour and 3-hour rain to a 0–1 hazard value. V uses weighted site conditions. Scores are indicators, not percentages or probabilities.
        </p>
      </section>

      <section className="proof-trust-grid" aria-label="AI use, limits and sources">
        <Frame className="proof-trust-card proof-ai">
          <span className="f0-kicker">WHERE AI IS USED</span>
          <h2>DRAWING READING ONLY</h2>
          <p>Vision extraction is cross-checked against deterministic text rules. Low-confidence fields and disagreements go to a person; nothing is saved as confirmed without human review.</p>
          <span className="proof-ai__boundary">RISK · SCHEDULING · MATCHING · READINESS: RULE-BASED</span>
        </Frame>

        <Frame className="proof-trust-card">
          <span className="f0-kicker">LIMITS & DATA SOURCES</span>
          <ul className="proof-source-list">
            <li><b>Rain & elevation</b><span><a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a> archive and elevation data.</span></li>
            <li><b>Water distance</b><span><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> measurements.</span></li>
            <li><b>Flood labels</b><span>KNN India, The Hindu, The Week, The Hindu BusinessLine and Deccan Herald; citations are summarized in the back-test report.</span></li>
            <li><b>Planning zones</b><span>Curated illustrative circles from public reporting, not official flood maps.</span></li>
          </ul>
          <p className="proof-limit-note">
            Historical rain is not a live forecast. Risk is not a flood model; route facts can be missing; cycle times and partner capacity are estimates or declarations. A suggested backup still needs human, customer and contractual approval.
          </p>
        </Frame>
      </section>

      <section className="proof-glossary" aria-labelledby="proof-glossary-title">
        <div className="proof-section-heading">
          <div>
            <span className="f0-kicker">SIX TERMS FROM THE BRIEF</span>
            <h2 id="proof-glossary-title">GLOSSARY</h2>
          </div>
        </div>
        <dl>
          {glossary.map(([term, definition]) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{definition}</dd>
            </div>
          ))}
        </dl>
      </section>

      <footer className="proof-footer">
        <p>Want to inspect a live calculation? Open Exposure and use its “How was this calculated?” trace.</p>
        <Button variant="secondary" onClick={() => navigate('/app/exposure')}>Open Exposure →</Button>
      </footer>
    </main>
  )
}

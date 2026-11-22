import { useMemo } from 'react'
import { formatMoney } from '../../lib/format'
import { FallbackShield, OrderStatePill } from '../../components/domain'
import { orderLabel, orderStateLabel } from '../../lib/status'
import { Nameplate } from '../../components/primitives'

const CHART_X = 220
const CHART_W = 720
const ROW_H = 58
const MAX_HOURS = 168

function elapsedHours(timestamp, start) {
  const difference = new Date(timestamp).getTime() - new Date(start).getTime()
  return Number.isFinite(difference) ? Math.max(0, difference / 3_600_000) : 0
}

export function ShiftChart({ result, onOpenRecovery, readOnly = false }) {
  const rows = result?.orders || []
  const createdAt = result?.created_at || '1970-01-01T00:00:00Z'
  const chartHeight = Math.max(150, 74 + rows.length * ROW_H)
  const params = result?.params || {}
  const downtimeStart = Number(params.start_in_hours || 0)
  const downtimeEnd = downtimeStart + Number(params.duration_hours || 0)
  const xAt = (hours) => CHART_X + (Math.min(MAX_HOURS, hours) / MAX_HOURS) * CHART_W
  const ticks = useMemo(() => [0, 24, 48, 72, 96, 120, 144, 168], [])

  return (
    <div className="whatif-chart-scroll">
      <svg className="whatif-chart" viewBox={`0 0 980 ${chartHeight}`} role="img" aria-label="Baseline and stressed order completion schedule">
        <defs>
          <pattern id="whatif-downtime-hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="var(--c-midnight)" />
            <path d="M 0 0 V 8" stroke="var(--c-gold)" strokeWidth="2" />
          </pattern>
        </defs>
        <text x="12" y="24" className="whatif-chart__axis-label">ORDER</text>
        <text x={CHART_X} y="24" className="whatif-chart__axis-label">T+00</text>
        <text x={CHART_X + CHART_W} y="24" textAnchor="end" className="whatif-chart__axis-label">T+168 h</text>
        <rect x={xAt(downtimeStart)} y="34" width={Math.max(0, xAt(downtimeEnd) - xAt(downtimeStart))} height={chartHeight - 46} fill="url(#whatif-downtime-hatch)" opacity="0.32" />
        <text x={Math.min(xAt(downtimeStart) + 5, CHART_X + CHART_W - 145)} y="49" className="whatif-chart__downtime-label">
          DOWNTIME T+{downtimeStart} → T+{downtimeEnd}h
        </text>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={xAt(tick)} x2={xAt(tick)} y1="34" y2={chartHeight - 12} className="whatif-chart__gridline" />
            <text x={xAt(tick)} y={chartHeight - 1} textAnchor="middle" className="whatif-chart__tick">{tick}</text>
          </g>
        ))}
        {rows.map((order, index) => {
          const y = 74 + index * ROW_H
          const baseline = elapsedHours(order.baseline_finish_at, createdAt)
          const stressed = elapsedHours(order.stressed_finish_at, createdAt)
          const due = elapsedHours(order.due_at, createdAt)
          const overflow = Math.max(0, stressed - MAX_HOURS)
          return (
            <g key={order.order_id} className="whatif-chart__row">
              <text x="12" y={y + 5} className="whatif-chart__order">{orderLabel(order.order_id)}</text>
              <rect x={CHART_X} y={y - 12} width={Math.max(2, xAt(baseline) - CHART_X)} height="6" className="whatif-chart__baseline" />
              <rect x={CHART_X} y={y + 1} width={Math.max(2, xAt(stressed) - CHART_X)} height="11" className={order.state === 'LATE' ? 'whatif-chart__bar whatif-chart__bar--late' : 'whatif-chart__bar'} />
              {overflow > 0 && (
                <g className="whatif-chart__overflow" aria-label={`${overflow.toFixed(0)} hours beyond chart horizon`}>
                  <path d={`M ${CHART_X + CHART_W - 2} ${y + 1} l 10 5.5 l -10 5.5 z`} />
                  <text x={CHART_X + CHART_W + 12} y={y + 9}>+{overflow.toFixed(0)}h</text>
                  <title>{`${overflow.toFixed(1)} hours beyond T+168`}</title>
                </g>
              )}
              <line x1={xAt(due)} x2={xAt(due)} y1={y - 20} y2={y + 18} className="whatif-chart__due" />
              <text x={xAt(due) + 4} y={y - 10} className="whatif-chart__due-label">DUE</text>
              <text x={CHART_X} y={y + 27} className="whatif-chart__detail">
                base {baseline.toFixed(0)}h · stressed {stressed.toFixed(0)}h · {order.days_late == null ? orderStateLabel(order.state) : `+${order.days_late.toFixed(1)}d`}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="whatif-order-list">
        {rows.map((order) => (
          <article key={order.order_id}>
            <Nameplate>{orderLabel(order.order_id)}</Nameplate>
            <OrderStatePill value={order.state} />
            <span>{order.days_late == null ? 'On schedule' : `${order.days_late.toFixed(1)} days late`}</span>
            <span>{formatMoney(order.value_inr)}</span>
            <FallbackShield value={order.fallback_level} />
            <span className="whatif-order-list__backup">{order.best_backup || 'No backup'}</span>
            <button type="button" disabled={readOnly} onClick={() => onOpenRecovery(order.order_id)}>Open recovery →</button>
          </article>
        ))}
      </div>
    </div>
  )
}

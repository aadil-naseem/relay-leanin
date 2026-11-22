import { useId } from 'react'

export function Frame({ as: Element = 'section', className = '', children, ...props }) {
  return <Element className={`relay-frame ${className}`.trim()} {...props}>{children}</Element>
}

export function Button({
  variant = 'primary',
  size = 'medium',
  loading = false,
  disabled = false,
  children,
  className = '',
  ...props
}) {
  return (
    <button
      className={`relay-button relay-button--${variant} relay-button--${size} ${className}`.trim()}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <span className="relay-button__mark" aria-hidden="true">·</span>}
      {children}
    </button>
  )
}

export function Segmented({ value, options, onChange, label, className = '', disabled = false }) {
  return (
    <div className={`relay-segmented ${className}`.trim()} role="group" aria-label={label}>
      {options.map((option) => {
        const item = typeof option === 'object'
          ? option
          : { value: option, label: String(option) }
        return (
          <button
            key={item.value}
            type="button"
            className={value === item.value ? 'is-selected' : ''}
            aria-pressed={value === item.value}
            disabled={disabled}
            onClick={() => onChange?.(item.value)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

export function Chip({ tone = 'hair', children, className = '' }) {
  return <span className={`relay-chip relay-chip--${tone} ${className}`.trim()}>{children}</span>
}

export function Nameplate({ children, className = '' }) {
  return <span className={`relay-nameplate ${className}`.trim()}>{children}</span>
}

export function Stamp({ tone = 'sun', children, className = '' }) {
  return <span className={`relay-stamp relay-stamp--${tone} ${className}`.trim()}>{children}</span>
}

export function Tooltip({ label, children }) {
  return <span className="relay-tooltip" title={label}>{children}</span>
}

export function Drawer({ open, title, onClose, children, side = 'right', className = '' }) {
  if (!open) return null
  return (
    <div className="relay-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose?.()}>
      <section className={`relay-drawer relay-drawer--${side} ${className}`.trim()} role="dialog" aria-modal="true" aria-label={title}>
        <header className="relay-drawer__header">
          <h2>{title}</h2>
          <Button variant="ghost" size="small" aria-label="Close drawer" onClick={onClose}>×</Button>
        </header>
        <div className="relay-drawer__body">{children}</div>
      </section>
    </div>
  )
}

export function Dialog({ open, title, onClose, children, actions }) {
  if (!open) return null
  return (
    <div className="relay-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose?.()}>
      <section className="relay-dialog" role="dialog" aria-modal="true" aria-label={title}>
        <h2>{title}</h2>
        <div>{children}</div>
        {actions && <footer className="relay-dialog__actions">{actions}</footer>}
      </section>
    </div>
  )
}

export function Tabs({ value, tabs, onChange, label = 'Tabs' }) {
  return (
    <div className="relay-tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          type="button"
          role="tab"
          aria-selected={value === tab.value}
          className={value === tab.value ? 'is-selected' : ''}
          key={tab.value}
          onClick={() => onChange?.(tab.value)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export function Toggle({ checked, onChange, label, disabled = false }) {
  return (
    <label className={`relay-toggle ${disabled ? 'is-disabled' : ''}`}>
      <input type="checkbox" checked={Boolean(checked)} disabled={disabled} onChange={(event) => onChange?.(event.target.checked)} />
      <span className="relay-toggle__track" aria-hidden="true"><i /></span>
      <span>{label}</span>
    </label>
  )
}

export function Slider({ value, min = 0, max = 100, step = 1, onChange, label, ...props }) {
  const id = useId()
  return (
    <label className="relay-slider" htmlFor={id}>
      <span>{label}</span>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange?.(Number(event.target.value))}
        {...props}
      />
      <output>{value}</output>
    </label>
  )
}

export function Field({ label, id: providedId, hint, error, ...props }) {
  const generatedId = useId()
  const id = providedId || generatedId
  return (
    <label className={`relay-field ${error ? 'has-error' : ''}`} htmlFor={id}>
      <span>{label}</span>
      <input id={id} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined} {...props} />
      {error && <small id={`${id}-error`} role="alert">{error}</small>}
      {!error && hint && <small id={`${id}-hint`}>{hint}</small>}
    </label>
  )
}

export function Table({ columns, rows, getRowKey = (row, index) => row.id ?? index, caption }) {
  return (
    <div className="relay-table-wrap">
      <table className="relay-table">
        {caption && <caption>{caption}</caption>}
        <thead><tr>{columns.map((column) => <th key={column.key} scope="col">{column.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={getRowKey(row, index)}>
              {columns.map((column) => <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>)}
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={columns.length}>No records.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

export function Skeleton({ lines = 3, className = '' }) {
  return (
    <div className={`relay-skeleton ${className}`.trim()} aria-label="Loading" role="status">
      {Array.from({ length: lines }, (_, index) => <i key={index} />)}
    </div>
  )
}

export function Toast({ tone = 'info', children, onDismiss }) {
  return (
    <div className={`relay-toast relay-toast--${tone}`} role="status">
      <span>{children}</span>
      {onDismiss && <Button variant="ghost" size="small" aria-label="Dismiss notification" onClick={onDismiss}>×</Button>}
    </div>
  )
}

export function Kbd({ children }) {
  return <kbd className="relay-kbd">{children}</kbd>
}

const glyphs = {
  arrow: '→',
  check: '✓',
  clock: '◷',
  close: '×',
  upload: '↑',
  factory: '▦',
  lathe: '⟳',
  mill: '⌗',
  drill: '⊙',
  grinder: '⊜',
  furnace: '♨',
  flood: '≋',
  power: 'ϟ',
  water: '≈',
  road: '⊣',
  supplier: '▣',
}

export function Icon({ name, label, className = '' }) {
  const glyph = glyphs[name] || '·'
  return <span aria-label={label || name} role="img" className={`relay-icon relay-icon--${name} ${className}`.trim()}>{glyph}</span>
}

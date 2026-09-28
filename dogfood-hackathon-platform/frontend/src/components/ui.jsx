import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

/* ---------- data loading ---------- */

// Loads one or more endpoints together. `paths` is an object: { key: '/api/...' }.
export function useLoad(paths) {
  const key = JSON.stringify(paths)
  const [state, setState] = useState({ data: null, error: null, loading: true })

  const reload = useCallback(async () => {
    try {
      const entries = Object.entries(JSON.parse(key))
      const values = await Promise.all(entries.map(([, p]) => api(p)))
      setState({ data: Object.fromEntries(entries.map(([k], i) => [k, values[i]])), error: null, loading: false })
    } catch (e) {
      setState((s) => ({ ...s, error: e.message, loading: false }))
    }
  }, [key])

  useEffect(() => {
    reload()
  }, [reload])

  return { ...state, reload }
}

/* ---------- formatting ---------- */

export const fmtDate = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        hour: 'numeric',
        minute: '2-digit',
      })
    : '—'

export const fmtScore = (n) => (n === null || n === undefined ? '—' : Number(n).toFixed(2))

export function timeLeft(iso) {
  const ms = new Date(iso) - new Date()
  if (ms <= 0) return null
  const h = Math.floor(ms / 3_600_000)
  const m = Math.floor((ms % 3_600_000) / 60_000)
  return h >= 1 ? `${h}h ${m}m` : `${m}m`
}

/* ---------- small components ---------- */

const TONES = {
  eligible: ['ok', 'Eligible'],
  ineligible: ['bad', 'Ineligible'],
  pending: ['wait', 'Pending'],
  completed: ['ok', 'Completed'],
  awaiting_judges: ['wait', 'Waiting for a judge'],
  in_review: ['info', 'Being judged'],
  evaluated: ['ok', 'Judged'],
  ranked: ['ok', 'Ranked'],
  not_ranked: ['muted', 'Not ranked'],
  submissions_open: ['info', 'Submissions open'],
  judging: ['wait', 'Judging'],
  upcoming: ['muted', 'Upcoming'],
  results_published: ['ok', 'Results published'],
  published: ['ok', 'Published'],
  draft: ['wait', 'Draft'],
}

export function Badge({ status, tone, children }) {
  const [t, label] = TONES[status] || [tone || 'muted', status]
  return <span className={`badge badge-${tone || t}`}>{children || label}</span>
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

export function Alert({ tone = 'info', children, onClose }) {
  if (!children) return null
  return (
    <div className={`alert alert-${tone}`} role={tone === 'bad' ? 'alert' : 'status'}>
      <div>{children}</div>
      {onClose && (
        <button className="alert-close" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  )
}

export function Loading() {
  return <p className="loading">Loading…</p>
}

export function LoadError({ error, retry }) {
  return (
    <Alert tone="bad">
      {error}{' '}
      {retry && (
        <button className="link-btn" onClick={retry}>
          Try again
        </button>
      )}
    </Alert>
  )
}

export function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export function Progress({ value, max }) {
  const pct = max ? Math.round((value / max) * 100) : 0
  return (
    <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-fill" style={{ width: `${pct}%` }} />
    </div>
  )
}

// Wraps an async action with busy + error state.
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const run = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e.message)
      return undefined
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, setError, run }
}

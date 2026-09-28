import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { HOME_BY_ROLE, useAuth } from '../auth'
import { Alert, fmtDate, timeLeft, useAction } from '../components/ui'

const DEMO = [
  { label: 'Organizer', email: 'admin@dogfood.dev', password: 'Admin@123', note: 'Assign judges, publish results' },
  { label: 'Judge', email: 'judge@dogfood.dev', password: 'Judge@123', note: 'Score assigned projects' },
  { label: 'Participant', email: 'participant@dogfood.dev', password: 'Participant@123', note: 'Form a team, submit, see results' },
]

export function AuthAside() {
  const [event, setEvent] = useState(null)
  useEffect(() => {
    api('/api/hackathon').then(setEvent).catch(() => {})
  }, [])

  const left = event && timeLeft(event.submission_deadline)
  return (
    <aside className="auth-aside">
      <div className="auth-title">
        <span className="auth-72">72</span>
        <span className="auth-hours">hours</span>
      </div>
      <h2 className="auth-event">{event ? event.name : 'Dogfood 72-Hour Hackathon'}</h2>
      <p className="auth-tagline">{event?.tagline || 'Build something you’d use yourself.'}</p>
      {event && (
        <p className="auth-when">
          {event.results_published
            ? 'Results are out.'
            : left
              ? `Submissions close in ${left}`
              : 'Submissions are closed. Judging is underway.'}
          <br />
          <span className="auth-dates">
            {fmtDate(event.starts_at)} to {fmtDate(event.ends_at)}
          </span>
        </p>
      )}
    </aside>
  )
}

export default function Login() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { busy, error, run } = useAction()

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />

  const go = (e, p) =>
    run(async () => {
      const u = await signIn(e, p)
      navigate(HOME_BY_ROLE[u.role], { replace: true })
    })

  return (
    <div className="auth">
      <AuthAside />
      <section className="auth-panel">
        <div className="auth-box">
          <h1>Sign in</h1>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              go(email, password)
            }}
          >
            <label className="field">
              <span>Email</span>
              <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <Alert tone="bad">{error}</Alert>
            <button className="btn btn-primary btn-block" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <p className="muted small">
            New participant? <Link to="/register">Create an account</Link>
          </p>

          <div className="demo">
            <h2>Try a demo account</h2>
            <p className="muted small">One click signs you in. Each role sees a different part of the flow.</p>
            <div className="demo-list">
              {DEMO.map((d) => (
                <button key={d.email} className="demo-btn" disabled={busy} onClick={() => go(d.email, d.password)}>
                  <span className="demo-role">{d.label}</span>
                  <span className="demo-note">{d.note}</span>
                  <span className="demo-cred">
                    {d.email} / {d.password}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

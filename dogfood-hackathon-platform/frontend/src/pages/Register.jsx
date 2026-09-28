import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from '../auth'
import { Alert, useAction } from '../components/ui'
import { AuthAside } from './Login'

export default function Register() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const { busy, error, run } = useAction()

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <div className="auth">
      <AuthAside />
      <section className="auth-panel">
        <div className="auth-box">
          <h1>Create a participant account</h1>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              run(async () => {
                await register(form)
                navigate('/participant', { replace: true })
              })
            }}
          >
            <label className="field">
              <span>Full name</span>
              <input value={form.full_name} onChange={set('full_name')} autoComplete="name" required minLength={2} />
            </label>
            <label className="field">
              <span>Email</span>
              <input type="email" value={form.email} onChange={set('email')} autoComplete="email" required />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={set('password')}
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={72}
              />
              <small className="muted">At least 8 characters, with a letter and a number.</small>
            </label>
            <Alert tone="bad">{error}</Alert>
            <button className="btn btn-primary btn-block" disabled={busy}>
              {busy ? 'Creating account…' : 'Create account'}
            </button>
          </form>
          <p className="muted small">
            Already registered? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </section>
    </div>
  )
}

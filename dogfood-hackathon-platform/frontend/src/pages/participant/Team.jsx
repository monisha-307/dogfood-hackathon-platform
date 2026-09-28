import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { Alert, Badge, fmtDate, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'

function NoTeam({ onDone }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const create = useAction()
  const join = useAction()

  return (
    <div className="grid-2">
      <section className="card">
        <h2 className="card-title">Create a team</h2>
        <p className="muted">You’ll be the team lead and get an invite code to share.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create.run(async () => onDone(await api('/api/teams', { method: 'POST', body: { name } })))
          }}
        >
          <label className="field">
            <span>Team name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={80} />
          </label>
          <Alert tone="bad">{create.error}</Alert>
          <button className="btn btn-primary" disabled={create.busy}>
            {create.busy ? 'Creating…' : 'Create team'}
          </button>
        </form>
      </section>
      <section className="card">
        <h2 className="card-title">Join a team</h2>
        <p className="muted">Ask your team lead for their six-character invite code.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            join.run(async () => onDone(await api('/api/teams/join', { method: 'POST', body: { invite_code: code } })))
          }}
        >
          <label className="field">
            <span>Invite code</span>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              required
              minLength={4}
              maxLength={16}
              className="input-code"
              placeholder="e.g. 7F3A0C"
            />
          </label>
          <Alert tone="bad">{join.error}</Alert>
          <button className="btn" disabled={join.busy}>
            {join.busy ? 'Joining…' : 'Join team'}
          </button>
        </form>
      </section>
    </div>
  )
}

export default function TeamPage() {
  const { data, error, loading, reload } = useLoad({ team: '/api/teams/me', event: '/api/hackathon' })
  const [copied, setCopied] = useState(false)
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const team = data.team.team
  const event = data.event

  if (!team)
    return (
      <>
        <PageHeader title="Team" subtitle={`Teams have ${event.min_team_size} to ${event.max_team_size} members. You can be on one team.`} />
        <NoTeam onDone={reload} />
      </>
    )

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(team.invite_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked; the code is visible anyway */
    }
  }

  return (
    <>
      <PageHeader
        title={team.name}
        subtitle={`${team.members.length} of ${event.max_team_size} members`}
        actions={
          team.has_submission ? (
            <Link className="btn" to="/participant/submission">View submission</Link>
          ) : (
            <Link className="btn btn-primary" to="/participant/submission">Submit project</Link>
          )
        }
      />
      <div className="grid-2">
        <section className="card">
          <h2 className="card-title">Members</h2>
          <ul className="people">
            {team.members.map((m) => (
              <li key={m.id}>
                <div>
                  <strong>{m.full_name}</strong> {m.is_lead && <Badge tone="dark">Lead</Badge>}
                  <div className="muted small">{m.email}</div>
                </div>
                <span className="muted small">Joined {fmtDate(m.joined_at)}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2 className="card-title">Invite teammates</h2>
          {team.submission_locked ? (
            <p className="muted">Judging has started on your project, so the team is closed to new members.</p>
          ) : team.members.length >= event.max_team_size ? (
            <p className="muted">Your team is full.</p>
          ) : (
            <>
              <p className="muted">Share this code. Teammates enter it on their Team page.</p>
              <div className="invite">
                <code className="invite-code">{team.invite_code}</code>
                <button className="btn" onClick={copy}>{copied ? 'Copied' : 'Copy code'}</button>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  )
}

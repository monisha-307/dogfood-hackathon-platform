import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import { Badge, fmtDate, LoadError, Loading, PageHeader, timeLeft, useLoad } from '../../components/ui'

function buildSteps({ team, submission, result, certificate, published }) {
  const stage = submission?.stage
  return [
    { name: 'Team', done: !!team, detail: team ? team.name : 'Create or join one' },
    { name: 'Submit', done: !!submission, detail: submission ? submission.title : 'Add your project' },
    {
      name: 'Eligibility',
      done: submission?.eligibility_status === 'eligible',
      blocked: submission?.eligibility_status === 'ineligible',
      detail: !submission ? 'Checked on submit' : submission.eligibility_status === 'eligible' ? 'All checks passed' : 'Needs fixes',
    },
    {
      name: 'Judging',
      done: stage === 'evaluated' || published,
      detail: stage === 'in_review' ? 'Being scored' : stage === 'awaiting_judges' ? 'Waiting for a judge' : stage === 'evaluated' ? 'Scored' : 'After eligibility',
    },
    { name: 'Results', done: published && !!result, detail: published ? (result?.rank ? `Rank ${result.rank}` : 'Published') : 'Not published yet' },
    { name: 'Certificate', done: !!certificate, detail: certificate ? certificate.title : 'Issued with results' },
  ]
}

function nextAction({ team, submission, published, certificate }) {
  if (!team) return { text: 'Start by creating a team or joining one with an invite code.', to: '/participant/team', cta: 'Set up your team' }
  if (!submission) return { text: 'Your team is ready. Submit your project before the deadline.', to: '/participant/submission', cta: 'Submit project' }
  if (submission.eligibility_status === 'ineligible')
    return { text: 'Your submission failed an eligibility check. Fix it to be judged.', to: '/participant/submission', cta: 'Fix submission' }
  if (published && certificate) return { text: 'Results are out.', to: '/participant/results', cta: 'See your result' }
  if (published) return { text: 'Results are out.', to: '/participant/results', cta: 'See results' }
  if (submission.stage === 'awaiting_judges') return { text: 'You’re eligible. The organizers will assign a judge next.' }
  if (submission.stage === 'in_review') return { text: 'A judge is scoring your project now.' }
  return { text: 'Your project has been scored. Results appear here once the organizers publish them.' }
}

export default function ParticipantHome() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad({
    event: '/api/hackathon',
    team: '/api/teams/me',
    sub: '/api/submissions/me',
    result: '/api/results/me',
    cert: '/api/certificates/me',
  })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const ctx = {
    team: data.team.team,
    submission: data.sub.submission,
    result: data.result.result,
    published: data.result.published,
    certificate: data.cert.certificate,
  }
  const steps = buildSteps(ctx)
  const currentIndex = steps.findIndex((s) => !s.done)
  const action = nextAction(ctx)
  const event = data.event
  const left = timeLeft(event.submission_deadline)

  return (
    <>
      <PageHeader
        title={`Hi, ${user.full_name.split(' ')[0]}`}
        subtitle={event.name}
        actions={<Badge status={event.phase} />}
      />

      <section className="card">
        <h2 className="card-title">Your progress</h2>
        <ol className="track">
          {steps.map((s, i) => {
            const state = s.done ? 'done' : s.blocked ? 'blocked' : i === currentIndex ? 'current' : 'todo'
            return (
              <li key={s.name} className={`track-step track-${state}`}>
                <span className="track-num">{s.done ? '✓' : i + 1}</span>
                <span className="track-name">{s.name}</span>
                <span className="track-detail">{s.detail}</span>
              </li>
            )
          })}
        </ol>
        <div className="next">
          <p>{action.text}</p>
          {action.to && (
            <Link className="btn btn-primary" to={action.to}>
              {action.cta}
            </Link>
          )}
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <h2 className="card-title">About the event</h2>
          <p>{event.description}</p>
          <dl className="facts">
            <dt>Submission deadline</dt>
            <dd>
              {fmtDate(event.submission_deadline)}
              {left && !event.results_published && <span className="muted"> ({left} left)</span>}
            </dd>
            <dt>Team size</dt>
            <dd>
              {event.min_team_size} to {event.max_team_size} people
            </dd>
          </dl>
        </section>
        <section className="card">
          <h2 className="card-title">How you’ll be judged</h2>
          <table className="table table-compact">
            <tbody>
              {event.criteria.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.name}</strong>
                    <div className="muted small">{c.description}</div>
                  </td>
                  <td className="num">{c.max_score} pts</td>
                </tr>
              ))}
              <tr className="row-total">
                <td>Total</td>
                <td className="num">{event.max_total} pts</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </>
  )
}

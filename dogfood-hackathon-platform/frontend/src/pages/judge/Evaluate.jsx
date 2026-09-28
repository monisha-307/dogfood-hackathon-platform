import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import { Alert, Badge, fmtDate, fmtScore, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'

function SubmissionDetails({ sub }) {
  return (
    <section className="card">
      <h2 className="card-title">{sub.title}</h2>
      <p className="muted small">
        {sub.team.name}, submitted {fmtDate(sub.submitted_at)}
      </p>
      <p className="prose">{sub.summary}</p>
      <dl className="facts">
        <dt>Source code</dt>
        <dd>
          <a href={sub.repo_url} target="_blank" rel="noreferrer noopener">{sub.repo_url}</a>
        </dd>
        {sub.demo_url && (
          <>
            <dt>Demo</dt>
            <dd>
              <a href={sub.demo_url} target="_blank" rel="noreferrer noopener">{sub.demo_url}</a>
            </dd>
          </>
        )}
        {sub.tech_stack && (
          <>
            <dt>Tech stack</dt>
            <dd>{sub.tech_stack}</dd>
          </>
        )}
        <dt>Eligibility</dt>
        <dd>
          <Badge status={sub.eligibility_status} />
        </dd>
      </dl>
    </section>
  )
}

function ScoreForm({ assignmentId, criteria, maxTotal, onDone }) {
  const [scores, setScores] = useState(() => Object.fromEntries(criteria.map((c) => [c.id, ''])))
  const [feedback, setFeedback] = useState('')
  const submit = useAction()

  const entered = criteria.filter((c) => scores[c.id] !== '')
  const raw = entered.reduce((sum, c) => sum + Number(scores[c.id]), 0)
  const allScored = entered.length === criteria.length
  const normalized = maxTotal ? (raw / maxTotal) * 100 : 0

  const setScore = (c, value) => {
    if (value === '') return setScores({ ...scores, [c.id]: '' })
    const n = Math.max(0, Math.min(c.max_score, Math.round(Number(value))))
    setScores({ ...scores, [c.id]: Number.isFinite(n) ? n : '' })
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (!window.confirm('Submit these scores? You can’t change them afterwards.')) return
    submit.run(async () => {
      await api(`/api/judge/assignments/${assignmentId}/evaluation`, {
        method: 'POST',
        body: {
          scores: criteria.map((c) => ({ criterion_id: c.id, score: Number(scores[c.id]) })),
          feedback,
        },
      })
      onDone()
    })
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <h2 className="card-title">Score this project</h2>
      <fieldset disabled={submit.busy}>
        {criteria.map((c) => (
          <div key={c.id} className="criterion">
            <div className="criterion-head">
              <label htmlFor={`score-${c.id}`}>
                <strong>{c.name}</strong>
                <span className="muted small"> {c.description}</span>
              </label>
              <span className="criterion-value num">
                <input
                  id={`score-${c.id}`}
                  type="number"
                  min={0}
                  max={c.max_score}
                  step={1}
                  value={scores[c.id]}
                  onChange={(e) => setScore(c, e.target.value)}
                  required
                  className="input-score"
                />
                <span className="muted"> / {c.max_score}</span>
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={c.max_score}
              step={1}
              value={scores[c.id] === '' ? 0 : scores[c.id]}
              onChange={(e) => setScore(c, e.target.value)}
              aria-label={`${c.name} slider`}
              className={scores[c.id] === '' ? 'range range-unset' : 'range'}
            />
          </div>
        ))}

        <div className="live-total" aria-live="polite">
          <div>
            <span className="muted small">Raw total</span>
            <strong className="num">
              {raw} / {maxTotal}
            </strong>
          </div>
          <div>
            <span className="muted small">Normalized</span>
            <strong className="num">{allScored ? fmtScore(normalized) : '—'}</strong>
          </div>
          <p className="muted small">
            normalized = raw ÷ max × 100{allScored ? ` = ${raw} ÷ ${maxTotal} × 100` : ''}
          </p>
        </div>

        <label className="field">
          <span>Feedback for the team <em className="muted">(optional, shown anonymously)</em></span>
          <textarea rows={3} maxLength={1000} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
          <small className="muted">{feedback.length} / 1000</small>
        </label>
        <Alert tone="bad">{submit.error}</Alert>
        <button className="btn btn-primary" disabled={!allScored || submit.busy}>
          {submit.busy ? 'Submitting…' : allScored ? 'Submit evaluation' : `Score all ${criteria.length} criteria to submit`}
        </button>
      </fieldset>
    </form>
  )
}

function SubmittedScores({ evaluation }) {
  return (
    <section className="card">
      <h2 className="card-title">Your evaluation</h2>
      <p className="muted small">Submitted {fmtDate(evaluation.submitted_at)}. Scores are final.</p>
      <table className="table table-compact">
        <tbody>
          {evaluation.scores.map((s) => (
            <tr key={s.criterion_id}>
              <td>{s.name}</td>
              <td className="num">
                {s.score} / {s.max_score}
              </td>
            </tr>
          ))}
          <tr className="row-total">
            <td>Raw total</td>
            <td className="num">
              {evaluation.raw_total} / {evaluation.max_total}
            </td>
          </tr>
          <tr className="row-total">
            <td>Normalized</td>
            <td className="num">{fmtScore(evaluation.normalized_score)}</td>
          </tr>
        </tbody>
      </table>
      {evaluation.feedback && <blockquote>{evaluation.feedback}</blockquote>}
    </section>
  )
}

export default function Evaluate() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useLoad({ d: `/api/judge/assignments/${id}` })
  const [justSubmitted, setJustSubmitted] = useState(false)

  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const { assignment, criteria, max_total, results_published } = data.d
  const sub = assignment.submission

  return (
    <>
      <PageHeader
        title={sub.title}
        subtitle={sub.team.name}
        actions={
          <>
            <Badge status={assignment.status} />
            <Link className="btn" to="/judge">All projects</Link>
          </>
        }
      />
      {justSubmitted && (
        <Alert tone="ok" onClose={() => setJustSubmitted(false)}>
          Evaluation submitted.{' '}
          <button className="link-btn" onClick={() => navigate('/judge')}>Back to your list</button>
        </Alert>
      )}
      <div className="grid-main">
        <SubmissionDetails sub={sub} />
        {assignment.evaluation ? (
          <SubmittedScores evaluation={assignment.evaluation} />
        ) : results_published ? (
          <Alert tone="info">Results are published, so scoring is closed.</Alert>
        ) : (
          <ScoreForm
            assignmentId={assignment.id}
            criteria={criteria}
            maxTotal={max_total}
            onDone={async () => {
              setJustSubmitted(true)
              await reload()
            }}
          />
        )}
      </div>
    </>
  )
}

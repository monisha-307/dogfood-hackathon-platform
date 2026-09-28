import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { Alert, Badge, Empty, fmtDate, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'

const EMPTY = { title: '', summary: '', repo_url: '', demo_url: '', tech_stack: '' }
const MIN_SUMMARY = 50

export function EligibilityList({ checks }) {
  if (!checks?.length) return null
  return (
    <ul className="checks">
      {checks.map((c) => (
        <li key={c.rule} className={c.passed ? 'check-ok' : 'check-bad'}>
          <span className="check-icon" aria-hidden="true">{c.passed ? '✓' : '✕'}</span>
          <div>
            <strong>{c.rule}</strong>
            <div className="small">{c.detail}</div>
          </div>
          <span className="sr-only">{c.passed ? 'passed' : 'failed'}</span>
        </li>
      ))}
    </ul>
  )
}

export default function SubmissionPage() {
  const { data, error, loading, reload } = useLoad({ sub: '/api/submissions/me', event: '/api/hackathon' })
  const [form, setForm] = useState(EMPTY)
  const [saved, setSaved] = useState(null)
  const save = useAction()

  const submission = data?.sub.submission

  useEffect(() => {
    if (submission) {
      const { title, summary, repo_url, demo_url, tech_stack } = submission
      setForm({ title, summary, repo_url, demo_url, tech_stack })
    }
  }, [submission])

  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  if (!data.sub.has_team)
    return (
      <>
        <PageHeader title="Submission" />
        <Empty
          title="You need a team first"
          action={<Link className="btn btn-primary" to="/participant/team">Set up your team</Link>}
        >
          Every project is submitted by a team, even a team of one.
        </Empty>
      </>
    )

  const published = data.event.results_published
  const locked = submission?.locked || published
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const summaryLen = form.summary.trim().length

  const onSubmit = (e) => {
    e.preventDefault()
    setSaved(null)
    save.run(async () => {
      const res = await api('/api/submissions/me', { method: 'PUT', body: form })
      setSaved(res.submission.eligibility_status)
      await reload()
    })
  }

  return (
    <>
      <PageHeader
        title="Submission"
        subtitle={submission ? `${submission.team.name}, last saved ${fmtDate(submission.updated_at)}` : 'One submission per team. You can edit it until judging starts.'}
        actions={submission && <Badge status={submission.stage} />}
      />

      {saved === 'eligible' && <Alert tone="ok" onClose={() => setSaved(null)}>Submitted. Your project passed every eligibility check.</Alert>}
      {saved === 'ineligible' && <Alert tone="bad" onClose={() => setSaved(null)}>Saved, but it isn’t eligible yet. Fix the failed checks below and submit again.</Alert>}

      <div className="grid-main">
        <section className="card">
          <h2 className="card-title">{locked ? 'Your project' : submission ? 'Edit your project' : 'Submit your project'}</h2>
          {locked && (
            <Alert tone="info">
              {published ? 'Results are published. Submissions are closed.' : 'A judge has been assigned, so your submission is locked.'}
            </Alert>
          )}
          <form onSubmit={onSubmit}>
            <fieldset disabled={locked || save.busy}>
              <label className="field">
                <span>Project title</span>
                <input value={form.title} onChange={set('title')} required minLength={2} maxLength={120} />
              </label>
              <label className="field">
                <span>Summary</span>
                <textarea rows={5} value={form.summary} onChange={set('summary')} required maxLength={4000} />
                <small className={summaryLen >= MIN_SUMMARY ? 'muted' : 'warn-text'}>
                  {summaryLen} / {MIN_SUMMARY} characters minimum. Say what it does and who it’s for.
                </small>
              </label>
              <label className="field">
                <span>Source code link</span>
                <input type="url" value={form.repo_url} onChange={set('repo_url')} required placeholder="https://github.com/you/project" />
              </label>
              <label className="field">
                <span>Demo link <em className="muted">(optional)</em></span>
                <input type="url" value={form.demo_url} onChange={set('demo_url')} placeholder="https://" />
              </label>
              <label className="field">
                <span>Tech stack <em className="muted">(optional)</em></span>
                <input value={form.tech_stack} onChange={set('tech_stack')} placeholder="React, FastAPI, SQLite" />
              </label>
              <Alert tone="bad">{save.error}</Alert>
              {!locked && (
                <button className="btn btn-primary" disabled={save.busy}>
                  {save.busy ? 'Checking…' : submission ? 'Update submission' : 'Submit project'}
                </button>
              )}
            </fieldset>
          </form>
        </section>

        <section className="card">
          <h2 className="card-title">Eligibility</h2>
          {submission ? (
            <>
              <p>
                <Badge status={submission.eligibility_status} />
              </p>
              <EligibilityList checks={submission.eligibility_checks} />
            </>
          ) : (
            <p className="muted">
              When you submit, we check the deadline, your team size, the summary length and your links. Anything that
              fails is listed here with how to fix it.
            </p>
          )}
        </section>
      </div>
    </>
  )
}

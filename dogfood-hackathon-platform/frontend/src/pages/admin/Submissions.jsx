import { useState } from 'react'
import { api } from '../../api'
import { Alert, Badge, Empty, fmtDate, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'
import { EligibilityList } from '../participant/Submission'

const FILTERS = [
  ['all', 'All'],
  ['awaiting_judges', 'Needs a judge'],
  ['in_review', 'Being judged'],
  ['evaluated', 'Judged'],
  ['ineligible', 'Ineligible'],
]

function AssignJudge({ sub, judges, disabled, onChange }) {
  const available = judges.filter((j) => !sub.assignments.some((a) => a.judge.id === j.id))
  const [judgeId, setJudgeId] = useState('')
  const action = useAction()

  if (sub.eligibility_status !== 'eligible') return <p className="muted small">Only eligible submissions can be judged.</p>
  if (!available.length) return <p className="muted small">Every judge is assigned.</p>

  const selected = judgeId || String(available[0].id)
  return (
    <div>
      <div className="inline-form">
        <label className="sr-only" htmlFor={`judge-${sub.id}`}>Judge</label>
        <select id={`judge-${sub.id}`} value={selected} onChange={(e) => setJudgeId(e.target.value)} disabled={disabled || action.busy}>
          {available.map((j) => (
            <option key={j.id} value={j.id}>{j.full_name}</option>
          ))}
        </select>
        <button
          className="btn btn-primary btn-sm"
          disabled={disabled || action.busy}
          onClick={() =>
            action.run(async () => {
              await api('/api/admin/assignments', {
                method: 'POST',
                body: { submission_id: sub.id, judge_id: Number(selected) },
              })
              onChange(`Assigned to ${sub.title}.`)
            })
          }
        >
          {action.busy ? 'Assigning…' : 'Assign judge'}
        </button>
      </div>
      <Alert tone="bad">{action.error}</Alert>
    </div>
  )
}

export default function AdminSubmissions() {
  const { data, error, loading, reload } = useLoad({ s: '/api/admin/submissions', j: '/api/admin/judges', h: '/api/hackathon' })
  const [filter, setFilter] = useState('all')
  const [notice, setNotice] = useState(null)
  const remove = useAction()

  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const published = data.h.results_published
  const subs = data.s.submissions.filter((s) => filter === 'all' || s.stage === filter)
  const changed = async (msg) => {
    setNotice(msg)
    await reload()
  }

  return (
    <>
      <PageHeader title="Submissions & judges" subtitle="Check eligibility and send eligible projects to judges." />
      {published && <Alert tone="info">Results are published. Unpublish them on the Results page to change assignments.</Alert>}
      <Alert tone="ok" onClose={() => setNotice(null)}>{notice}</Alert>
      <Alert tone="bad">{remove.error}</Alert>

      <div className="filters" role="group" aria-label="Filter submissions">
        {FILTERS.map(([key, label]) => {
          const count = key === 'all' ? data.s.submissions.length : data.s.submissions.filter((s) => s.stage === key).length
          return (
            <button key={key} className={filter === key ? 'chip chip-on' : 'chip'} aria-pressed={filter === key} onClick={() => setFilter(key)}>
              {label} <span className="chip-count">{count}</span>
            </button>
          )
        })}
      </div>

      {subs.length === 0 ? (
        <Empty title={filter === 'all' ? 'No submissions yet' : 'Nothing here'}>
          {filter === 'all' ? 'Teams submit from their Submission page.' : 'No submissions match this filter.'}
        </Empty>
      ) : (
        subs.map((s) => (
          <section key={s.id} className="card sub-card">
            <div className="sub-head">
              <div>
                <h2 className="card-title">{s.title}</h2>
                <p className="muted small">
                  {s.team.name}, submitted {fmtDate(s.submitted_at)}
                </p>
              </div>
              <div className="badges">
                <Badge status={s.eligibility_status} />
                {s.eligibility_status === 'eligible' && <Badge status={s.stage} />}
              </div>
            </div>
            <p className="prose small">{s.summary}</p>
            <p className="small">
              <a href={s.repo_url} target="_blank" rel="noreferrer noopener">{s.repo_url}</a>
            </p>

            <div className="grid-2 sub-grid">
              <div>
                <h3 className="sub-label">Eligibility checks</h3>
                <EligibilityList checks={s.eligibility_checks} />
              </div>
              <div>
                <h3 className="sub-label">Judges</h3>
                {s.assignments.length === 0 && <p className="muted small">No judge assigned.</p>}
                <ul className="assignments">
                  {s.assignments.map((a) => (
                    <li key={a.id}>
                      <span>{a.judge.full_name}</span>
                      <Badge status={a.status} />
                      {a.status === 'pending' && !published && (
                        <button
                          className="link-btn small"
                          disabled={remove.busy}
                          onClick={() =>
                            remove.run(async () => {
                              await api(`/api/admin/assignments/${a.id}`, { method: 'DELETE' })
                              await changed(`Removed ${a.judge.full_name} from ${s.title}.`)
                            })
                          }
                        >
                          Remove
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <AssignJudge sub={s} judges={data.j.judges} disabled={published} onChange={changed} />
              </div>
            </div>
          </section>
        ))
      )}
    </>
  )
}

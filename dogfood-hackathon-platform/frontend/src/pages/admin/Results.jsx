import { useState } from 'react'
<<<<<<< HEAD
import { api } from '../../api'
=======
import { api, download } from '../../api'
>>>>>>> 97e6bd8 (Initial hackathon submission)
import Leaderboard from '../../components/Leaderboard'
import { Alert, Badge, Empty, fmtDate, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'

export default function AdminResults() {
  const { data, error, loading, reload } = useLoad({ r: '/api/admin/results' })
  const [notice, setNotice] = useState(null)
  const [confirmPending, setConfirmPending] = useState(false)
  const action = useAction()

  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const r = data.r
  const pending = r.pending_evaluations

  const call = (path, body, msg) =>
    action.run(async () => {
      await api(path, { method: 'POST', body })
      setConfirmPending(false)
      setNotice(msg)
      await reload()
    })

  const publish = () => {
    if (pending.length && !confirmPending) {
      setConfirmPending(true)
      return
    }
    call('/api/admin/results/publish', { allow_pending: pending.length > 0 }, 'Published. Participants can now see results and certificates.')
  }

  return (
    <>
      <PageHeader
        title="Results"
        subtitle={
          r.published
            ? `Published ${fmtDate(r.published_at)}`
            : r.calculated_at
              ? `Draft, last calculated ${fmtDate(r.calculated_at)}. Only you can see this.`
              : 'Not calculated yet.'
        }
        actions={
          <>
            <Badge status={r.published ? 'published' : 'draft'} />
            {!r.published && (
              <button className="btn" disabled={action.busy} onClick={() => call('/api/admin/results/calculate', undefined, 'Results recalculated.')}>
                Calculate results
              </button>
            )}
            {r.published ? (
              <button
                className="btn"
                disabled={action.busy}
                onClick={() => {
                  if (window.confirm('Unpublish? Participants will lose access to results and certificates until you publish again.'))
                    call('/api/admin/results/unpublish', undefined, 'Unpublished. Results are a draft again.')
                }}
              >
                Unpublish
              </button>
            ) : (
              <button className="btn btn-primary" disabled={action.busy} onClick={publish}>
                Publish results
              </button>
            )}
          </>
        }
      />

      <Alert tone="ok" onClose={() => setNotice(null)}>{notice}</Alert>
      <Alert tone="bad">{action.error}</Alert>

      {!r.published && pending.length > 0 && (
        <div className={confirmPending ? 'alert alert-bad' : 'alert alert-wait'} role="status">
          <div>
            <strong>{pending.length} {pending.length === 1 ? 'evaluation is' : 'evaluations are'} still pending.</strong>
            <ul className="tight">
              {pending.map((p) => (
                <li key={p.assignment_id}>
                  {p.judge} on {p.submission}
                </li>
              ))}
            </ul>
            {confirmPending ? (
              <>
                <p>
                  If you publish now, projects are ranked on completed scores only. Projects with no completed score
                  aren’t ranked.
                </p>
                <div className="btn-row">
                  <button className="btn btn-primary" disabled={action.busy} onClick={publish}>
                    Publish anyway
                  </button>
                  <button className="btn" onClick={() => setConfirmPending(false)}>
                    Wait for judges
                  </button>
                </div>
              </>
            ) : (
              <p className="small">You can wait, or publish now with completed scores only.</p>
            )}
          </div>
        </div>
      )}

      <section className="card formula">
        <h2 className="card-title">How scores are calculated</h2>
        <ol className="formula-steps">
          <li>
            Each judge scores every criterion. <code>normalized = raw total ÷ max possible × 100</code>
          </li>
          <li>
            A project’s final score is the average of its judges’ normalized scores.{' '}
            <code>final = average(normalized scores)</code>
          </li>
          <li>Projects are ranked by final score. Equal scores share a rank. Ineligible or unscored projects aren’t ranked.</li>
        </ol>
      </section>

      <section className="card">
        <h2 className="card-title">{r.published ? 'Published ranking' : 'Ranking preview'}</h2>
        {r.results.length ? (
          <Leaderboard results={r.results} />
        ) : (
          <Empty title="Nothing calculated yet">Calculate results to preview the ranking.</Empty>
        )}
      </section>
<<<<<<< HEAD
=======

      <section className="card">
        <h2 className="card-title">Export data</h2>
        <p className="muted">
          The ranking as a spreadsheet, or a full snapshot of the event (teams, submissions, scores, results and
          certificates). Password hashes are never included.
        </p>
        <div className="btn-row">
          <button
            className="btn"
            disabled={action.busy}
            onClick={() => action.run(() => download('/api/admin/export/results.csv', 'dogfood-results.csv'))}
          >
            Download results (CSV)
          </button>
          <button
            className="btn"
            disabled={action.busy}
            onClick={() => action.run(() => download('/api/admin/export/event.json', 'dogfood-event-export.json'))}
          >
            Download full export (JSON)
          </button>
        </div>
      </section>
>>>>>>> 97e6bd8 (Initial hackathon submission)
    </>
  )
}

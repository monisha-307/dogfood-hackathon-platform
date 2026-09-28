import { Link } from 'react-router-dom'
import { Badge, fmtDate, LoadError, Loading, PageHeader, Progress, Stat, timeLeft, useLoad } from '../../components/ui'

export default function AdminHome() {
  const { data, error, loading, reload } = useLoad({ o: '/api/admin/overview' })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const { hackathon: h, counts: c, next_steps } = data.o
  const left = timeLeft(h.submission_deadline)

  return (
    <>
      <PageHeader
        title={h.name}
        subtitle={`Submissions close ${fmtDate(h.submission_deadline)}${left ? ` (${left} left)` : ''}`}
        actions={<Badge status={h.phase} />}
      />

      <div className="stats">
        <Stat label="Participants" value={c.participants} hint={c.participants_without_team ? `${c.participants_without_team} without a team` : 'All on teams'} />
        <Stat label="Teams" value={c.teams} />
        <Stat label="Submissions" value={c.submissions} hint={`${c.eligible} eligible, ${c.ineligible} ineligible`} />
        <Stat label="Evaluations done" value={`${c.evaluations_completed}/${c.evaluations_total}`} hint={`${c.judges} judge(s)`} />
      </div>

      <div className="grid-2">
        <section className="card">
          <h2 className="card-title">What to do next</h2>
          <ul className="next-steps">
            {next_steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
          <div className="btn-row">
            {c.unassigned > 0 && <Link className="btn btn-primary" to="/admin/submissions">Assign judges</Link>}
            <Link className={c.unassigned > 0 ? 'btn' : 'btn btn-primary'} to="/admin/results">
              {h.results_published ? 'View results' : 'Calculate and publish'}
            </Link>
          </div>
        </section>
        <section className="card">
          <h2 className="card-title">Judging progress</h2>
          <p>
            <strong>{c.evaluations_completed}</strong> of {c.evaluations_total} evaluations submitted
            {c.evaluations_pending > 0 && <span className="muted">, {c.evaluations_pending} pending</span>}.
          </p>
          <Progress value={c.evaluations_completed} max={c.evaluations_total} />
          <p className="muted small">
            {c.unassigned > 0
              ? `${c.unassigned} eligible submission(s) have no judge yet.`
              : 'Every eligible submission has at least one judge.'}
          </p>
          <Link to="/admin/scores">See every score</Link>
        </section>
      </div>
    </>
  )
}

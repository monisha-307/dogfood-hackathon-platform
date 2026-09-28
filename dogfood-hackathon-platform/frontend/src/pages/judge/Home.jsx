import { Link } from 'react-router-dom'
import { Badge, Empty, fmtDate, fmtScore, LoadError, Loading, PageHeader, Progress, useLoad } from '../../components/ui'

export default function JudgeHome() {
  const { data, error, loading, reload } = useLoad({ a: '/api/judge/assignments' })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const { assignments, total, completed, pending } = data.a

  return (
    <>
      <PageHeader
        title="Assigned projects"
        subtitle={
          total === 0
            ? 'Nothing assigned yet.'
            : pending === 0
              ? 'All done. Thanks for judging.'
              : `${pending} left to score.`
        }
      />

      {total > 0 && (
        <section className="card judge-progress">
          <div className="judge-progress-row">
            <strong>
              {completed} of {total} scored
            </strong>
            <span className="muted small">Scores are final once submitted.</span>
          </div>
          <Progress value={completed} max={total} />
        </section>
      )}

      {total === 0 ? (
        <Empty title="No projects assigned">The organizers will assign projects to you. They’ll show up here.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Assigned</th>
                <th scope="col">Status</th>
                <th scope="col" className="num">Your score</th>
                <th scope="col"><span className="sr-only">Action</span></th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.submission.title}</strong>
                    <div className="muted small">{a.submission.team.name}</div>
                  </td>
                  <td className="small">{fmtDate(a.assigned_at)}</td>
                  <td>
                    <Badge status={a.status} />
                  </td>
                  <td className="num">{a.evaluation ? fmtScore(a.evaluation.normalized_score) : '—'}</td>
                  <td className="actions">
                    <Link className={a.status === 'pending' ? 'btn btn-primary btn-sm' : 'btn btn-sm'} to={`/judge/assignments/${a.id}`}>
                      {a.status === 'pending' ? 'Score project' : 'View scores'}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

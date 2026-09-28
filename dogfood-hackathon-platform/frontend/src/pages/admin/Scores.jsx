import { Badge, Empty, fmtDate, fmtScore, LoadError, Loading, PageHeader, useLoad } from '../../components/ui'

export default function AdminScores() {
  const { data, error, loading, reload } = useLoad({ e: '/api/admin/evaluations' })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const rows = data.e.evaluations
  return (
    <>
      <PageHeader title="Scores" subtitle="Every judge assignment and what was scored." />
      {rows.length === 0 ? (
        <Empty title="No judges assigned yet">Assign judges on the Submissions page.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Judge</th>
                <th scope="col">Status</th>
                <th scope="col">Criteria</th>
                <th scope="col" className="num">Raw</th>
                <th scope="col" className="num">Normalized</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.assignment_id}>
                  <td>
                    <strong>{r.submission.title}</strong>
                    <div className="muted small">{r.submission.team}</div>
                  </td>
                  <td>{r.judge.full_name}</td>
                  <td>
                    <Badge status={r.status} />
                    {r.evaluation && <div className="muted small">{fmtDate(r.evaluation.submitted_at)}</div>}
                  </td>
                  <td className="small">
                    {r.evaluation ? (
                      <>
                        <ul className="criteria-inline">
                          {r.evaluation.scores.map((s) => (
                            <li key={s.criterion_id}>
                              {s.name} <span className="num">{s.score}/{s.max_score}</span>
                            </li>
                          ))}
                        </ul>
                        {r.evaluation.feedback && <p className="muted feedback-inline">“{r.evaluation.feedback}”</p>}
                      </>
                    ) : (
                      <span className="muted">Waiting for scores</span>
                    )}
                  </td>
                  <td className="num">{r.evaluation ? `${r.evaluation.raw_total} / ${r.evaluation.max_total}` : '—'}</td>
                  <td className="num score-cell">{r.evaluation ? fmtScore(r.evaluation.normalized_score) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

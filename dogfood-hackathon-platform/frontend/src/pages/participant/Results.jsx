import { Link } from 'react-router-dom'
import Leaderboard, { Calculation } from '../../components/Leaderboard'
import { Empty, fmtScore, LoadError, Loading, PageHeader, useLoad } from '../../components/ui'

export default function MyResults() {
  const { data, error, loading, reload } = useLoad({
    mine: '/api/results/me',
    board: '/api/results',
    team: '/api/teams/me',
    sub: '/api/submissions/me',
  })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const { mine, board } = data
  const team = data.team.team
  const stage = data.sub.submission?.stage

  if (!mine.published)
    return (
      <>
        <PageHeader title="Results" />
        <Empty title="Results aren’t published yet">
          {stage === 'evaluated'
            ? 'Your project has been scored. You’ll see your rank here as soon as the organizers publish.'
            : stage === 'in_review'
              ? 'A judge is scoring your project now.'
              : 'Once judging finishes and the organizers publish, your rank and feedback appear here.'}
        </Empty>
      </>
    )

  const result = mine.result
  return (
    <>
      <PageHeader
        title="Results"
        subtitle="Final scores are published."
        actions={
          result && (
            <Link className="btn btn-primary" to="/participant/certificate">
              View certificate
            </Link>
          )
        }
      />

      {result ? (
        <section className="card result-hero">
          <div className="result-rank">
            <span className="result-label">Rank</span>
            <span className="result-big">{result.rank ?? '—'}</span>
            {result.rank && <span className="muted">of {mine.total_ranked}</span>}
          </div>
          <div className="result-rank">
            <span className="result-label">Final score</span>
            <span className="result-big">{fmtScore(result.final_score)}</span>
            <span className="muted">out of 100</span>
          </div>
          <div className="result-calc">
            <span className="result-label">{team?.name}, {result.submission.title}</span>
            {result.status === 'ranked' ? (
              <Calculation breakdown={result.breakdown} finalScore={result.final_score} />
            ) : (
              <p>{result.note}</p>
            )}
          </div>
        </section>
      ) : (
        <Empty title="Your team didn’t submit a project">Only submitted projects are ranked.</Empty>
      )}

      {mine.feedback.length > 0 && (
        <section className="card">
          <h2 className="card-title">Judge feedback</h2>
          {mine.feedback.map((f) => (
            <div key={f.judge} className="feedback">
              <div className="feedback-head">
                <strong>{f.judge}</strong>
                <span className="num">{fmtScore(f.normalized_score)} / 100</span>
              </div>
              <table className="table table-compact">
                <tbody>
                  {f.scores.map((s) => (
                    <tr key={s.criterion_id}>
                      <td>{s.name}</td>
                      <td className="num">
                        {s.score} / {s.max_score}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {f.feedback && <blockquote>{f.feedback}</blockquote>}
            </div>
          ))}
        </section>
      )}

      <section className="card">
        <h2 className="card-title">Leaderboard</h2>
        <Leaderboard results={board.results} highlightTeamId={team?.id} />
      </section>
    </>
  )
}

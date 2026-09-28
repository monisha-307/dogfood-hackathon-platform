import { Badge, fmtScore } from './ui'

export function Calculation({ breakdown, finalScore }) {
  if (!breakdown?.length) return <span className="muted">No scores yet</span>
  const parts = breakdown.map((b) => fmtScore(b.normalized_score))
  return (
    <div className="calc">
      {breakdown.map((b, i) => (
        <div key={i} className="calc-line">
          <span className="calc-judge">{b.judge}</span>
          <span className="num">
            {b.raw_total} / {b.max_total} × 100 = {fmtScore(b.normalized_score)}
          </span>
        </div>
      ))}
      <div className="calc-line calc-final">
        <span className="calc-judge">Final</span>
        <span className="num">
          {breakdown.length > 1 ? `average(${parts.join(', ')}) = ` : ''}
          {fmtScore(finalScore)}
        </span>
      </div>
    </div>
  )
}

export default function Leaderboard({ results, highlightTeamId }) {
  if (!results?.length) return <p className="muted">No results to show.</p>
  return (
    <div className="table-wrap">
      <table className="table leaderboard">
        <thead>
          <tr>
            <th scope="col">Rank</th>
            <th scope="col">Team and project</th>
            <th scope="col">How the score was calculated</th>
            <th scope="col" className="num">Final score</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr
              key={r.id}
              className={[r.rank === 1 ? 'row-first' : '', r.team.id === highlightTeamId ? 'row-mine' : ''].join(' ')}
            >
              <td className="rank-cell">{r.rank ? <span className="rank">{r.rank}</span> : <Badge status="not_ranked" />}</td>
              <td>
                <strong>{r.team.name}</strong>
                <div className="muted small">{r.submission.title}</div>
                {r.note && <div className="small warn-text">{r.note}</div>}
              </td>
              <td>
                <Calculation breakdown={r.breakdown} finalScore={r.final_score} />
              </td>
              <td className="num score-cell">{fmtScore(r.final_score)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

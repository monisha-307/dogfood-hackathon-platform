import { Badge, Empty, fmtDate, LoadError, Loading, PageHeader, useLoad } from '../../components/ui'

export default function AdminTeams() {
  const { data, error, loading, reload } = useLoad({ t: '/api/admin/teams' })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />
  const teams = data.t.teams

  return (
    <>
      <PageHeader title="Teams" subtitle={`${teams.length} team(s)`} />
      {teams.length === 0 ? (
        <Empty title="No teams yet">Participants create teams from their Team page.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Team</th>
                <th scope="col">Members</th>
                <th scope="col">Invite code</th>
                <th scope="col">Submission</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((t) => (
                <tr key={t.id}>
                  <td>
                    <strong>{t.name}</strong>
                    <div className="muted small">Created {fmtDate(t.created_at)}</div>
                  </td>
                  <td>
                    {t.members.map((m) => (
                      <div key={m.id}>
                        {m.full_name} {m.is_lead && <Badge tone="dark">Lead</Badge>}
                      </div>
                    ))}
                  </td>
                  <td><code>{t.invite_code}</code></td>
                  <td>
                    {t.submission ? (
                      <>
                        {t.submission.title} <Badge status={t.submission.eligibility_status} />
                      </>
                    ) : (
                      <span className="muted">Not submitted</span>
                    )}
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

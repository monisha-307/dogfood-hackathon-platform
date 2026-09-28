import { useState } from 'react'
import { Badge, Empty, fmtDate, LoadError, Loading, PageHeader, useLoad } from '../../components/ui'

export default function AdminParticipants() {
  const { data, error, loading, reload } = useLoad({ p: '/api/admin/participants' })
  const [q, setQ] = useState('')
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const all = data.p.participants
  const needle = q.trim().toLowerCase()
  const people = needle
    ? all.filter((p) => [p.full_name, p.email, p.team?.name].some((v) => v?.toLowerCase().includes(needle)))
    : all

  return (
    <>
      <PageHeader
        title="Participants"
        subtitle={`${all.length} registered, ${all.filter((p) => !p.team).length} without a team`}
        actions={
          <input
            type="search"
            className="search"
            placeholder="Search name, email or team"
            aria-label="Search participants"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        }
      />
      {people.length === 0 ? (
        <Empty title="No matches">Try a different search.</Empty>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Team</th>
                <th scope="col">Registered</th>
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}>
                  <td><strong>{p.full_name}</strong></td>
                  <td>{p.email}</td>
                  <td>
                    {p.team ? (
                      <>
                        {p.team.name} {p.is_lead && <Badge tone="dark">Lead</Badge>}
                      </>
                    ) : (
                      <Badge tone="wait">No team</Badge>
                    )}
                  </td>
                  <td className="small">{fmtDate(p.joined_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const NAV = {
  participant: [
    ['/participant', 'Overview', true],
    ['/participant/team', 'Team'],
    ['/participant/submission', 'Submission'],
    ['/participant/results', 'Results'],
    ['/participant/certificate', 'Certificate'],
  ],
  judge: [['/judge', 'Assigned projects', true]],
  admin: [
    ['/admin', 'Overview', true],
    ['/admin/submissions', 'Submissions & judges'],
    ['/admin/scores', 'Scores'],
    ['/admin/results', 'Results'],
    ['/admin/criteria', 'Criteria'],
    ['/admin/teams', 'Teams'],
    ['/admin/participants', 'Participants'],
  ],
}

const ROLE_LABEL = { admin: 'Organizer', judge: 'Judge', participant: 'Participant' }

export default function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = () => {
    signOut()
    navigate('/login')
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">Dogfood</span>
          <span className="brand-sub">72-hour hackathon</span>
        </div>
        <nav className="nav" aria-label="Main">
          {NAV[user.role].map(([to, label, end]) => (
            <NavLink key={to} to={to} end={end} className="nav-link">
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="whoami">
          <div className="whoami-name">{user.full_name}</div>
          <div className="whoami-role">{ROLE_LABEL[user.role]}</div>
          <div className="whoami-email">{user.email}</div>
          <button className="btn btn-ghost-dark" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main" id="main">
        <Outlet />
      </main>
    </div>
  )
}

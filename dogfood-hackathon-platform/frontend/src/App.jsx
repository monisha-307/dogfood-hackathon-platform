import { Navigate, Route, Routes } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from './auth'
import Layout from './components/Layout'
import { Loading } from './components/ui'
import Login from './pages/Login'
import Register from './pages/Register'
import Verify from './pages/Verify'
import ParticipantHome from './pages/participant/Home'
import TeamPage from './pages/participant/Team'
import SubmissionPage from './pages/participant/Submission'
import MyResults from './pages/participant/Results'
import CertificatePage from './pages/participant/Certificate'
import JudgeHome from './pages/judge/Home'
import Evaluate from './pages/judge/Evaluate'
import AdminHome from './pages/admin/Home'
import AdminSubmissions from './pages/admin/Submissions'
import AdminScores from './pages/admin/Scores'
import AdminResults from './pages/admin/Results'
import AdminCriteria from './pages/admin/Criteria'
import AdminTeams from './pages/admin/Teams'
import AdminParticipants from './pages/admin/Participants'

function RequireRole({ role }) {
  const { user, ready } = useAuth()
  if (!ready) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={HOME_BY_ROLE[user.role]} replace />
  return <Layout />
}

function Home() {
  const { user, ready } = useAuth()
  if (!ready) return <Loading />
  return <Navigate to={user ? HOME_BY_ROLE[user.role] : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify/:code" element={<Verify />} />

      <Route path="/participant" element={<RequireRole role="participant" />}>
        <Route index element={<ParticipantHome />} />
        <Route path="team" element={<TeamPage />} />
        <Route path="submission" element={<SubmissionPage />} />
        <Route path="results" element={<MyResults />} />
        <Route path="certificate" element={<CertificatePage />} />
      </Route>

      <Route path="/judge" element={<RequireRole role="judge" />}>
        <Route index element={<JudgeHome />} />
        <Route path="assignments/:id" element={<Evaluate />} />
      </Route>

      <Route path="/admin" element={<RequireRole role="admin" />}>
        <Route index element={<AdminHome />} />
        <Route path="submissions" element={<AdminSubmissions />} />
        <Route path="scores" element={<AdminScores />} />
        <Route path="results" element={<AdminResults />} />
        <Route path="criteria" element={<AdminCriteria />} />
        <Route path="teams" element={<AdminTeams />} />
        <Route path="participants" element={<AdminParticipants />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

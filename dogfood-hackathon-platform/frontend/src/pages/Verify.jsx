import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { fmtDate } from '../components/ui'

// Public page: anyone holding a certificate code can check it's genuine.
export default function Verify() {
  const { code } = useParams()
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    api(`/api/certificates/verify/${encodeURIComponent(code)}`)
      .then((d) => setState({ cert: d.certificate }))
      .catch((e) => setState({ error: e.message }))
  }, [code])

  return (
    <div className="verify">
      <div className="verify-box">
        <p className="brand-inline">Dogfood certificate check</p>
        {state.loading && <p>Checking…</p>}
        {state.error && (
          <>
            <h1>Not verified</h1>
            <p>{state.error} Check the code and try again.</p>
          </>
        )}
        {state.cert && (
          <>
            <h1>Verified</h1>
            <p>
              This certificate was issued to <strong>{state.cert.recipient}</strong> ({state.cert.team}) as{' '}
              <strong>{state.cert.title}</strong> at {state.cert.hackathon}.
            </p>
            <p className="muted small">
              Code {state.cert.verification_code}, issued {fmtDate(state.cert.issued_at)}
            </p>
          </>
        )}
        <Link to="/login">Go to sign in</Link>
      </div>
    </div>
  )
}

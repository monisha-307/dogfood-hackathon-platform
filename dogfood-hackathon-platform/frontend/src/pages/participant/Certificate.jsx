import { Link } from 'react-router-dom'
import { Empty, fmtScore, LoadError, Loading, PageHeader, useLoad } from '../../components/ui'

const ORDINAL = { 1: '1st', 2: '2nd', 3: '3rd' }
const ordinal = (n) => ORDINAL[n] || `${n}th`

export default function CertificatePage() {
  const { data, error, loading, reload } = useLoad({ cert: '/api/certificates/me' })
  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const cert = data.cert.certificate
  if (!cert)
    return (
      <>
        <PageHeader title="Certificate" />
        <Empty
          title={data.cert.published ? 'No certificate for this account' : 'Certificates come with the results'}
          action={<Link className="btn" to="/participant">Back to overview</Link>}
        >
          {data.cert.published
            ? 'Certificates go to members of teams that submitted a project.'
            : 'Every member of a team that submitted gets one when the organizers publish results.'}
        </Empty>
      </>
    )

  const verifyUrl = `${window.location.origin}/verify/${cert.verification_code}`
  const issued = new Date(cert.issued_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })
  const isPlacing = cert.kind !== 'participation'

  return (
    <>
      <div className="no-print">
        <PageHeader
          title="Certificate"
          subtitle="Print it or save it as a PDF from the print dialog."
          actions={<button className="btn btn-primary" onClick={() => window.print()}>Print or save as PDF</button>}
        />
      </div>

      <article className="certificate" aria-label="Certificate">
        <div className="cert-top">
          <span className="cert-event">{cert.hackathon}</span>
          <span className="cert-kind">{isPlacing ? cert.title : 'Participant'}</span>
        </div>
        <p className="cert-lead">This certifies that</p>
        <h2 className="cert-name">{cert.recipient}</h2>
        <p className="cert-body">
          of team <strong>{cert.team}</strong>{' '}
          {cert.rank
            ? <>placed <strong>{ordinal(cert.rank)}</strong> with <strong>{cert.project}</strong>, scoring <span className="nowrap">{fmtScore(cert.final_score)} out of 100</span>.</>
            : <>took part and submitted <strong>{cert.project}</strong>.</>}
        </p>
        <div className="cert-foot">
          <div>
            <span className="cert-foot-label">Issued</span>
            {issued}
          </div>
          <div className="cert-verify">
            <span className="cert-foot-label">Verify at</span>
            {verifyUrl}
          </div>
        </div>
      </article>
    </>
  )
}

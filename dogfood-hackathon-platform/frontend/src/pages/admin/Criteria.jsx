import { useState } from 'react'
import { api } from '../../api'
import { Alert, LoadError, Loading, PageHeader, useAction, useLoad } from '../../components/ui'

function CriterionRow({ c, disabled, onChange }) {
  const [form, setForm] = useState({ name: c.name, description: c.description, max_score: c.max_score })
  const action = useAction()
  const dirty = form.name !== c.name || form.description !== c.description || Number(form.max_score) !== c.max_score
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <tr>
      <td>
        <input aria-label="Name" value={form.name} onChange={set('name')} disabled={disabled} maxLength={80} />
      </td>
      <td>
        <input aria-label="Description" value={form.description} onChange={set('description')} disabled={disabled} maxLength={255} />
      </td>
      <td className="num">
        <input aria-label="Max points" type="number" min={1} max={100} value={form.max_score} onChange={set('max_score')} disabled={disabled} className="input-score" />
      </td>
      <td className="actions">
        <button
          className="btn btn-sm btn-primary"
          disabled={disabled || !dirty || action.busy}
          onClick={() =>
            action.run(async () => {
              await api(`/api/admin/criteria/${c.id}`, {
                method: 'PUT',
                body: { ...form, max_score: Number(form.max_score) },
              })
              onChange(`Saved ${form.name}.`)
            })
          }
        >
          Save
        </button>
        <button
          className="btn btn-sm"
          disabled={disabled || action.busy}
          onClick={() => {
            if (!window.confirm(`Delete “${c.name}”?`)) return
            action.run(async () => {
              await api(`/api/admin/criteria/${c.id}`, { method: 'DELETE' })
              onChange(`Deleted ${c.name}.`)
            })
          }}
        >
          Delete
        </button>
        {action.error && <div className="small bad-text">{action.error}</div>}
      </td>
    </tr>
  )
}

export default function AdminCriteria() {
  const { data, error, loading, reload } = useLoad({ c: '/api/admin/criteria', h: '/api/hackathon' })
  const [form, setForm] = useState({ name: '', description: '', max_score: 10 })
  const [notice, setNotice] = useState(null)
  const add = useAction()

  if (loading) return <Loading />
  if (error) return <LoadError error={error} retry={reload} />

  const { criteria, max_total, evaluations_submitted } = data.c
  const published = data.h.results_published
  const changed = async (msg) => {
    setNotice(msg)
    await reload()
  }

  return (
    <>
      <PageHeader title="Judging criteria" subtitle={`${criteria.length} criteria, ${max_total} points in total`} />
      <Alert tone="ok" onClose={() => setNotice(null)}>{notice}</Alert>
      {published && <Alert tone="info">Results are published. Unpublish them to edit criteria.</Alert>}
      {!published && evaluations_submitted > 0 && (
        <Alert tone="wait">
          {evaluations_submitted} evaluation(s) are already submitted. They keep the criteria they were scored on, and
          every score is normalized to 100, so final scores stay comparable. New evaluations use the criteria below.
        </Alert>
      )}

      <section className="card">
        <div className="table-wrap">
          <table className="table table-edit">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">What judges look for</th>
                <th scope="col" className="num">Max points</th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) => (
                <CriterionRow key={`${c.id}-${c.max_score}-${c.name}`} c={c} disabled={published} onChange={changed} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {!published && (
        <section className="card">
          <h2 className="card-title">Add a criterion</h2>
          <form
            className="inline-form wrap"
            onSubmit={(e) => {
              e.preventDefault()
              add.run(async () => {
                await api('/api/admin/criteria', { method: 'POST', body: { ...form, max_score: Number(form.max_score) } })
                setForm({ name: '', description: '', max_score: 10 })
                await changed(`Added ${form.name}.`)
              })
            }}
          >
            <label className="field">
              <span>Name</span>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} maxLength={80} />
            </label>
            <label className="field grow">
              <span>What judges look for</span>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} maxLength={255} />
            </label>
            <label className="field">
              <span>Max points</span>
              <input type="number" min={1} max={100} value={form.max_score} onChange={(e) => setForm({ ...form, max_score: e.target.value })} required className="input-score" />
            </label>
            <button className="btn btn-primary" disabled={add.busy}>Add criterion</button>
          </form>
          <Alert tone="bad">{add.error}</Alert>
        </section>
      )}
    </>
  )
}

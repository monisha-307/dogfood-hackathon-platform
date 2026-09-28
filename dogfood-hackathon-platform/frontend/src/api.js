const TOKEN_KEY = 'dogfood.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

// FastAPI returns either a string or a list of pydantic errors.
function readableDetail(detail) {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : ''
        const msg = String(d.msg || '').replace(/^Value error, /, '')
        return field && field !== 'body' ? `${String(field).replace(/_/g, ' ')}: ${msg}` : msg
      })
      .join(' ')
  }
  return String(detail)
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error("Can't reach the server. Check that the app is running.")
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    /* empty body */
  }

  if (!res.ok) {
    if (res.status === 401 && token) window.dispatchEvent(new Event('dogfood:signed-out'))
    const err = new Error(readableDetail(data?.detail) || `Request failed (${res.status}).`)
    err.status = res.status
    throw err
  }
  return data
}

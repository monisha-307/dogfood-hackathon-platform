import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)

export const HOME_BY_ROLE = { admin: '/admin', judge: '/judge', participant: '/participant' }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  const signOut = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    if (!getToken()) {
      setReady(true)
      return
    }
    api('/api/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true))
  }, [])

  useEffect(() => {
    window.addEventListener('dogfood:signed-out', signOut)
    return () => window.removeEventListener('dogfood:signed-out', signOut)
  }, [signOut])

  const acceptSession = (data) => {
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }

  const signIn = async (email, password) =>
    acceptSession(await api('/api/auth/login', { method: 'POST', body: { email, password } }))

  const register = async (payload) =>
    acceptSession(await api('/api/auth/register', { method: 'POST', body: payload }))

  return (
    <AuthContext.Provider value={{ user, ready, signIn, register, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

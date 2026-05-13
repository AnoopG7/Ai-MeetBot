import { useState, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface UserProfile {
  user_id: string
  email: string
  display_name: string
}

interface AuthResponse {
  access_token: string
  user_id: string
  email: string
  display_name: string
}

interface AuthPageProps {
  onAuth: (user: UserProfile, token: string) => void
  onGuest: () => void
}

export function AuthPage({ onAuth, onGuest }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'register') {
        const res = await fetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, display_name: displayName, password }),
        })
        if (!res.ok) {
          const body = await res.json()
          throw new Error(body.detail || 'Registration failed')
        }
        const data: AuthResponse = await res.json()
        onAuth({ user_id: data.user_id, email: data.email, display_name: data.display_name }, data.access_token)
      } else {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        })
        if (!res.ok) {
          const body = await res.json()
          throw new Error(body.detail || 'Login failed')
        }
        const data: AuthResponse = await res.json()
        onAuth({ user_id: data.user_id, email: data.email, display_name: data.display_name }, data.access_token)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }, [mode, email, displayName, password, onAuth])

  return (
    <div style={{ padding: 48, maxWidth: 380, margin: '0 auto', color: '#e8edf5' }}>
      <h1 style={{ textAlign: 'center', fontSize: 24, marginBottom: 4 }}>Finance Advisor</h1>
      <p style={{ textAlign: 'center', color: '#8892a8', marginBottom: 28, fontSize: 14 }}>
        {mode === 'login' ? 'Sign in to continue' : 'Create an account'}
      </p>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={fieldStyle}
        />
        {mode === 'register' && (
          <input
            type="text"
            placeholder="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            style={fieldStyle}
          />
        )}
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          style={fieldStyle}
        />
        {error && <p style={{ color: '#ef4444', margin: 0, fontSize: 13 }}>{error}</p>}
        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
        </button>
      </form>
      <div style={{ textAlign: 'center', marginTop: 12 }}>
        <button
          onClick={onGuest}
          style={{
            ...btnStyle,
            background: '#2d6a4f',
            marginBottom: 8,
          }}
        >
          Continue as Guest
        </button>
        <br />
        <button
          onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}
          style={{
            background: 'none', border: 'none', color: '#6366f1',
            cursor: 'pointer', fontSize: 13, padding: 0,
          }}
        >
          {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign In'}
        </button>
      </div>
    </div>
  )
}

const fieldStyle: React.CSSProperties = {
  padding: '10px 14px',
  fontSize: 14,
  borderRadius: 8,
  border: '1px solid #1e2a3a',
  background: '#131820',
  color: '#e8edf5',
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
}

const btnStyle: React.CSSProperties = {
  padding: '12px',
  fontSize: 15,
  fontWeight: 500,
  borderRadius: 8,
  border: 'none',
  background: '#6366f1',
  color: '#fff',
  cursor: 'pointer',
  width: '100%',
  boxSizing: 'border-box',
}

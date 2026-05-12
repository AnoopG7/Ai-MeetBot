import { useState, useCallback } from 'react'

import {
  LiveKitRoom,
  AudioVisualizer,
  useRoomContext,
  RoomAudioRenderer,
  ControlBar,
} from '@livekit/components-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEFAULT_ROOM = 'finance-advisor'

interface TokenResponse {
  token: string
  url: string
  room: string
}

interface AuthResponse {
  access_token: string
  user_id: string
  email: string
  display_name: string
}

interface UserProfile {
  user_id: string
  email: string
  display_name: string
}

function RoomView() {
  const room = useRoomContext()

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <h2>Connected to: {room.name}</h2>
      <AudioVisualizer />
      <RoomAudioRenderer />
      <ControlBar controls={{ camera: false, screenShare: false, chat: false }} />
    </div>
  )
}

function AuthPage({ onAuth }: { onAuth: (user: UserProfile, token: string) => void }) {
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
    <div style={{ padding: 48, maxWidth: 400, margin: '0 auto' }}>
      <h1 style={{ textAlign: 'center' }}>Finance Advisor</h1>
      <p style={{ textAlign: 'center', color: '#666', marginBottom: 32 }}>
        {mode === 'login' ? 'Sign in to continue' : 'Create an account'}
      </p>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={inputStyle}
        />
        {mode === 'register' && (
          <input
            type="text"
            placeholder="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            style={inputStyle}
          />
        )}
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          style={inputStyle}
        />
        {error && <p style={{ color: 'red', margin: 0 }}>{error}</p>}
        <button type="submit" disabled={loading} style={buttonStyle}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
        </button>
      </form>
      <p style={{ textAlign: 'center', marginTop: 16 }}>
        {mode === 'login' ? (
          <>Don't have an account?{' '}<a href="#" onClick={(e) => { e.preventDefault(); setMode('register'); setError(null) }}>Register</a></>
        ) : (
          <>Already have an account?{' '}<a href="#" onClick={(e) => { e.preventDefault(); setMode('login'); setError(null) }}>Sign In</a></>
        )}
      </p>
    </div>
  )
}

function App() {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const stored = localStorage.getItem('finance_user')
    return stored ? JSON.parse(stored) : null
  })
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem('finance_token'))
  const [livekitToken, setLivekitToken] = useState<string | null>(null)
  const [serverUrl, setServerUrl] = useState<string>('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAuth = useCallback((user: UserProfile, token: string) => {
    setUser(user)
    setAccessToken(token)
    localStorage.setItem('finance_user', JSON.stringify(user))
    localStorage.setItem('finance_token', token)
  }, [])

  const handleLogout = useCallback(() => {
    setUser(null)
    setAccessToken(null)
    setLivekitToken(null)
    localStorage.removeItem('finance_user')
    localStorage.removeItem('finance_token')
  }, [])

  const connect = useCallback(async () => {
    if (!accessToken) return
    setConnecting(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/livekit/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ room: DEFAULT_ROOM }),
      })
      if (!res.ok) {
        if (res.status === 401) {
          handleLogout()
          throw new Error('Session expired. Please sign in again.')
        }
        throw new Error(`Token request failed: ${res.status} ${res.statusText}`)
      }
      const data: TokenResponse = await res.json()
      setLivekitToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
    } finally {
      setConnecting(false)
    }
  }, [accessToken, handleLogout])

  if (!user) {
    return <AuthPage onAuth={handleAuth} />
  }

  if (livekitToken && serverUrl) {
    return (
      <LiveKitRoom
        token={livekitToken}
        serverUrl={serverUrl}
        connect={true}
        audio={true}
        video={false}
      >
        <RoomView />
      </LiveKitRoom>
    )
  }

  return (
    <div style={{ padding: 48, maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <h1>Finance Advisor</h1>
        <button onClick={handleLogout} style={{ ...buttonStyle, background: '#666', padding: '8px 16px', fontSize: 14 }}>
          Sign Out
        </button>
      </div>
      <p style={{ marginBottom: 8, color: '#666' }}>
        Signed in as <strong>{user.display_name}</strong> ({user.email})
      </p>
      <p style={{ marginBottom: 24, color: '#666' }}>
        Talk to your AI personal finance advisor
      </p>
      {error && (
        <p style={{ color: 'red', marginBottom: 16 }}>{error}</p>
      )}
      <button
        onClick={connect}
        disabled={connecting}
        style={{
          ...buttonStyle,
          cursor: connecting ? 'not-allowed' : 'pointer',
        }}
      >
        {connecting ? 'Connecting...' : 'Start Conversation'}
      </button>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '10px 14px',
  fontSize: 15,
  borderRadius: 6,
  border: '1px solid #ccc',
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
}

const buttonStyle: React.CSSProperties = {
  padding: '12px 32px',
  fontSize: 16,
  borderRadius: 8,
  border: 'none',
  background: '#0066cc',
  color: '#fff',
}

export default App

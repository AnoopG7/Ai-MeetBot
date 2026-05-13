import { useState, useCallback, useRef, useEffect } from 'react'

import type { LocalTrackPublication, RemoteTrackPublication } from 'livekit-client'

import {
  LiveKitRoom,
  useRoomContext,
  useLocalParticipant,
  BarVisualizer,
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

function log(area: string, msg: string, data?: unknown) {
  console.log(`[FinanceAdvisor][${area}] ${msg}`, data ?? '')
}

function speakText(text: string) {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0
    window.speechSynthesis.speak(utterance)
  }
}

// ──────────────────────────────────────────────
// Styles
// ──────────────────────────────────────────────
const theme = {
  bg: '#0b0e14',
  surface: '#131820',
  surface2: '#1a2230',
  border: '#1e2a3a',
  accent: '#6366f1',
  accentDim: '#4f46e5',
  text: '#e8edf5',
  textDim: '#8892a8',
  error: '#ef4444',
  green: '#22c55e',
} as const

function RoomView() {
  const room = useRoomContext()
  const { localParticipant } = useLocalParticipant()
  const [micOn, setMicOn] = useState(false)
  const [micBlocked, setMicBlocked] = useState(false)
  const [micBusy, setMicBusy] = useState(false)
  const [pttHeld, setPttHeld] = useState(false)
  const [msgs, setMsgs] = useState<{role: string; text: string}[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [msgs])

  useEffect(() => {
    log('room', `connected to ${room.name}`)
    const sub = (pub: RemoteTrackPublication) => { if (pub.kind === 'audio') log('track', 'agent audio in') }
    const pub = (pub: LocalTrackPublication) => { if (pub.kind === 'audio') log('track', 'local audio published') }
    room.on('trackSubscribed', sub)
    room.on('trackPublished', pub)
    return () => { room.off('trackSubscribed', sub); room.off('trackPublished', pub) }
  }, [room])

  const micUp = useCallback(async () => {
    if (!localParticipant || micBusy) return
    setMicBusy(true)
    setMicBlocked(false)
    try {
      await localParticipant.setMicrophoneEnabled(true)
      setMicOn(true)
    } catch {
      setMicBlocked(true)
    } finally {
      setMicBusy(false)
    }
  }, [localParticipant, micBusy])

  const micDown = useCallback(async () => {
    if (!localParticipant) return
    try {
      await localParticipant.setMicrophoneEnabled(false)
      setMicOn(false)
      setPttHeld(false)
    } catch (e) {
      log('mic', 'failed to disable microphone', e)
    }
  }, [localParticipant])

  const toggleMic = useCallback(() => micOn ? micDown() : micUp(), [micOn, micUp, micDown])

  const sendMsg = useCallback(async () => {
    const msg = input.trim()
    if (!msg || busy) return
    setInput('')
    setBusy(true)
    setMsgs((p) => [...p, { role: 'user', text: msg }])
    try {
      const r = await fetch(`${API_URL}/api/debug/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      })
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`)
      const d = await r.json()
      setMsgs((p) => [...p, { role: 'assistant', text: d.response }])
      speakText(d.response)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error'
      setMsgs((p) => [...p, { role: 'assistant', text: `Error: ${message}` }])
    } finally {
      setBusy(false)
    }
  }, [input, busy])

  const barState: 'silent' | 'speaking' = (!micOn || micBlocked) ? 'silent' : pttHeld ? 'speaking' : 'silent'

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      background: theme.bg, color: theme.text,
    }}>
      {/* ── header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: 52,
        borderBottom: `1px solid ${theme.border}`,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: theme.green, boxShadow: `0 0 6px ${theme.green}`,
          }}/>
          <span style={{ fontWeight: 600, fontSize: 15 }}>Finance Advisor</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <MicToggle
            on={micOn}
            blocked={micBlocked}
            busy={micBusy}
            onToggle={toggleMic}
          />
          <DisconnectButton />
        </div>
      </div>

      {/* ── body ── */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* chat */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0,
          borderRight: `1px solid ${theme.border}`,
        }}>
          <div ref={listRef} style={{
            flex: 1, overflowY: 'auto', padding: '16px 20px',
          }}>
            {msgs.length === 0 && (
              <div style={{ color: theme.textDim, fontSize: 13, textAlign: 'center', marginTop: 48, lineHeight: 1.8 }}>
                Type a question or enable your mic and speak.
                <br/>Agent responses will be spoken aloud.
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 10,
              }}>
                <div style={{
                  maxWidth: '70%',
                  padding: '10px 16px',
                  borderRadius: 16,
                  fontSize: 14,
                  lineHeight: 1.55,
                  background: m.role === 'user' ? theme.accent : theme.surface2,
                  color: m.role === 'user' ? '#fff' : theme.text,
                  borderBottomRightRadius: m.role === 'user' ? 4 : 16,
                  borderBottomLeftRadius: m.role === 'user' ? 16 : 4,
                }}>
                  {m.text}
                </div>
              </div>
            ))}
            {busy && (
              <div style={{ display: 'flex', gap: 4, padding: '8px 4px' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: theme.textDim, animation: 'none' }}/>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: theme.textDim }}/>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: theme.textDim }}/>
              </div>
            )}
          </div>
          <div style={{
            display: 'flex', gap: 8, padding: '12px 16px',
            borderTop: `1px solid ${theme.border}`,
          }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg() } }}
              placeholder="Ask about finance..."
              disabled={busy}
              style={{
                flex: 1, padding: '10px 14px', fontSize: 14, borderRadius: 10,
                border: `1px solid ${theme.border}`, background: theme.surface,
                color: theme.text, outline: 'none',
              }}
            />
            <button
              onClick={sendMsg}
              disabled={busy || !input.trim()}
              style={{
                padding: '10px 20px', fontSize: 14, fontWeight: 500,
                borderRadius: 10, border: 'none',
                background: busy || !input.trim() ? theme.surface2 : theme.accent,
                color: '#fff', cursor: busy || !input.trim() ? 'not-allowed' : 'pointer',
              }}
            >
              Send
            </button>
          </div>
        </div>

        {/* voice panel */}
        <div style={{
          width: 240, flexShrink: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 24, padding: 24,
        }}>
          <div style={{
            width: 140, height: 64, borderRadius: 12,
            background: theme.surface2, display: 'flex', alignItems: 'center',
            justifyContent: 'center', overflow: 'hidden',
          }}>
            <BarVisualizer
              state={barState}
              barCount={7}
              options={{ minHeight: 12, maxHeight: 56 }}
              style={{ width: 120, height: 48 }}
            />
          </div>

          <RecordButton
            enabled={micOn && !micBlocked}
            active={pttHeld}
            onHold={() => setPttHeld(true)}
            onRelease={() => setPttHeld(false)}
          />

          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: theme.textDim, marginBottom: 4 }}>
              {micBlocked ? 'Microphone blocked' : !micOn ? 'Mic off' : pttHeld ? 'Listening...' : 'Tap mic then hold to speak'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── sub-components ──

function MicToggle({ on, blocked, busy, onToggle }: {
  on: boolean; blocked: boolean; busy: boolean; onToggle: () => void
}) {
  const color = blocked ? theme.error : on ? theme.green : theme.textDim
  return (
    <button
      onClick={onToggle}
      disabled={busy}
      title={blocked ? 'Mic blocked — click to retry' : on ? 'Mute' : 'Unmute'}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500,
        border: `1px solid ${color}`, background: 'transparent',
        color, cursor: busy ? 'wait' : 'pointer', transition: 'all .15s',
        opacity: busy ? .6 : 1,
      }}
    >
      {busy ? '⏳' : blocked ? '🚫' : on ? '🎤' : '🔇'}
      <span>{blocked ? 'Blocked' : on ? 'On' : 'Off'}</span>
    </button>
  )
}

// We use a key to re-mount the button so stale refs don't persist
function RecordButton({ enabled, active, onHold, onRelease }: {
  enabled: boolean; active: boolean; onHold: () => void; onRelease: () => void
}) {
  return (
    <button
      key={String(enabled)}
      onMouseDown={enabled ? onHold : undefined}
      onMouseUp={enabled ? onRelease : undefined}
      onMouseLeave={enabled ? onRelease : undefined}
      onTouchStart={enabled ? onHold : undefined}
      onTouchEnd={enabled ? onRelease : undefined}
      style={{
        width: 80, height: 80, borderRadius: '50%', border: 'none',
        background: !enabled ? theme.surface2 : active ? theme.error : theme.accent,
        color: '#fff', fontSize: 30, cursor: enabled ? 'pointer' : 'not-allowed',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all .12s',
        opacity: enabled ? 1 : .35,
        transform: active ? 'scale(1.1)' : 'scale(1)',
        boxShadow: active ? `0 0 24px ${theme.error}66` : 'none',
      }}
    >
      {active ? '⏺' : '🎙️'}
    </button>
  )
}

function DisconnectButton() {
  const room = useRoomContext()
  return (
    <button
      onClick={() => room.disconnect()}
      style={{
        padding: '6px 12px', borderRadius: 8, fontSize: 12,
        border: `1px solid ${theme.border}`, background: 'transparent',
        color: theme.textDim, cursor: 'pointer',
      }}
    >
      Leave
    </button>
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
        log('auth', 'registering', email)
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
        log('auth', 'registered', { user_id: data.user_id })
        onAuth({ user_id: data.user_id, email: data.email, display_name: data.display_name }, data.access_token)
      } else {
        log('auth', 'logging in', email)
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
        log('auth', 'logged in', { user_id: data.user_id })
        onAuth({ user_id: data.user_id, email: data.email, display_name: data.display_name }, data.access_token)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
      log('auth', 'error', err)
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
  const [guestMode, setGuestMode] = useState(false)
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
    log('app', 'user authenticated', { user_id: user.user_id })
  }, [])

  const handleLogout = useCallback(() => {
    setUser(null)
    setAccessToken(null)
    setLivekitToken(null)
    localStorage.removeItem('finance_user')
    localStorage.removeItem('finance_token')
    log('app', 'user logged out')
  }, [])

  const connectGuest = useCallback(async () => {
    setConnecting(true)
    setError(null)
    log('app', 'requesting guest LiveKit token')
    try {
      const res = await fetch(`${API_URL}/api/livekit/token-guest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: DEFAULT_ROOM }),
      })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(body.detail || `Token request failed: ${res.status}`)
      }
      const data: TokenResponse = await res.json()
      log('app', 'LiveKit token received', { room: data.room, url: data.url })
      setLivekitToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      log('app', 'token request failed', err)
      setConnecting(false)
    }
  }, [])

  const connect = useCallback(async () => {
    if (!accessToken) return
    setConnecting(true)
    setError(null)
    log('app', 'requesting LiveKit token')
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
        const body = await res.json()
        throw new Error(body.detail || `Token request failed: ${res.status}`)
      }
      const data: TokenResponse = await res.json()
      log('app', 'LiveKit token received', { room: data.room, url: data.url })
      setLivekitToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      log('app', 'token request failed', err)
      setConnecting(false)
    }
  }, [accessToken, handleLogout])

  const handleDisconnect = useCallback(() => {
    setLivekitToken(null)
    setServerUrl('')
    setConnecting(false)
    log('app', 'disconnected from room')
  }, [])

  if (!user && !guestMode) {
    return (
      <div>
        <AuthPage onAuth={handleAuth} />
        <div style={{ marginTop: -20, textAlign: 'center' }}>
          <button onClick={() => { setGuestMode(true); connectGuest() }} style={{ ...buttonStyle, background: '#2d6a4f', padding: '10px 24px', fontSize: 15 }}>
            Skip — Continue as Guest
          </button>
        </div>
      </div>
    )
  }

  if (livekitToken && serverUrl) {
    return (
      <LiveKitRoom
        token={livekitToken}
        serverUrl={serverUrl}
        connect={true}
        audio={false}
        video={false}
        onError={(err) => {
          log('livekit', 'connection error', err)
        }}
        onDisconnected={() => {
          log('livekit', 'disconnected')
          handleDisconnect()
        }}
      >
        <RoomView />
      </LiveKitRoom>
    )
  }

  return (
    <div style={{ padding: 48, maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <h1>Finance Advisor</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={connectGuest} style={{ ...buttonStyle, background: '#2d6a4f', padding: '8px 16px', fontSize: 14 }}>
            Guest Mode
          </button>
          <button onClick={handleLogout} style={{ ...buttonStyle, background: '#666', padding: '8px 16px', fontSize: 14 }}>
            Sign Out
          </button>
        </div>
      </div>
      <p style={{ marginBottom: 8, color: '#666' }}>
        {guestMode ? 'Guest mode' : <>Signed in as <strong>{user!.display_name}</strong> ({user!.email})</>}
      </p>
      <p style={{ marginBottom: 24, color: '#666' }}>
        Talk to your AI personal finance advisor
      </p>
      {error && (
        <p style={{ color: 'red', marginBottom: 16 }}>{error}</p>
      )}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
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

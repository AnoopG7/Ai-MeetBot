import { useState, useCallback, useEffect, useRef } from 'react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useLocalParticipant,
} from '@livekit/components-react'
import type { RemoteAudioTrack } from 'livekit-client'
import { theme } from './theme'
import { useChat } from './hooks/useChat'
import { useTranscriptions } from './hooks/useTranscriptions'
import { ChatList } from './components/ChatList'
import { VoiceControls } from './components/VoiceControls'
import { AuthPage } from './components/AuthPage'
import type { UserProfile } from './components/AuthPage'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEFAULT_ROOM = 'finance-advisor'

interface TokenResponse {
  token: string
  url: string
  room: string
}

function RoomView() {
  const room = useRoomContext()
  const { localParticipant } = useLocalParticipant()
  const { messages, busy, sendText, upsertMessage } = useChat()
  const [input, setInput] = useState('')
  const [micOn, setMicOn] = useState(false)
  const [micBlocked, setMicBlocked] = useState(false)
  const [micBusy, setMicBusy] = useState(false)
  const [muted, setMuted] = useState(false)
  const mutedRef = useRef(false)
  const subCountRef = useRef(0)

  useEffect(() => {
    const sub = (track: any) => {
      subCountRef.current++
      console.log(`trackSubscribed #${subCountRef.current}: kind=${track.kind} source=${track.source}`)
    }
    room.on('trackSubscribed', sub)
    return () => { room.off('trackSubscribed', sub) }
  }, [room])

  const applyMute = useCallback((m: boolean) => {
    mutedRef.current = m
    for (const [, p] of room.remoteParticipants) {
      for (const [, pub] of p.trackPublications) {
        const track = pub.audioTrack
        if (track && (track as RemoteAudioTrack).setVolume) {
          (track as RemoteAudioTrack).setVolume(m ? 0 : 1)
        }
      }
    }
  }, [room])

  useEffect(() => {
    applyMute(muted)
    const sub = () => applyMute(mutedRef.current)
    room.on('trackSubscribed', sub)
    return () => { room.off('trackSubscribed', sub) }
  }, [muted, room, applyMute])

  function cleanToolCall(text: string): string {
    return text.replace(/<function=\w+>.*?<\/function>/g, '').trim()
  }

  useTranscriptions(room, (evt) => {
    const isLocal = evt.participantIdentity === localParticipant?.identity
    const display = cleanToolCall(evt.text)
    if (display) upsertMessage(isLocal ? 'user' : 'agent', evt.segmentId, display, evt.isFinal)
  })

  const toggleMic = useCallback(async () => {
    if (!localParticipant || micBusy) return
    setMicBusy(true)
    setMicBlocked(false)
    try {
      if (micOn) {
        await localParticipant.setMicrophoneEnabled(false)
        setMicOn(false)
      } else {
        await localParticipant.setMicrophoneEnabled(true)
        setMicOn(true)
      }
    } catch {
      setMicBlocked(true)
    } finally {
      setMicBusy(false)
    }
  }, [localParticipant, micOn, micBusy])

  const handleSend = useCallback(async () => {
    const msg = input.trim()
    if (!msg || busy) return
    setInput('')
    await sendText(msg)
  }, [input, busy, sendText])

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      background: theme.bg, color: theme.text,
    }}>
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
          }} />
          <span style={{ fontWeight: 600, fontSize: 15 }}>Finance Advisor</span>
        </div>
        <button
          onClick={() => setMuted(!muted)}
          title={muted ? 'Unmute' : 'Mute'}
          style={{
            padding: '6px 12px', borderRadius: 8, fontSize: 16,
            border: `1px solid ${theme.border}`, background: 'transparent',
            color: muted ? theme.textDim : theme.text, cursor: 'pointer',
            opacity: muted ? 0.5 : 1,
          }}
        >
          {muted ? '🔇' : '🔊'}
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <ChatList messages={messages} busy={busy} />

          <div style={{
            display: 'flex', gap: 8, padding: '12px 16px',
            borderTop: `1px solid ${theme.border}`,
          }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder="Ask about finance..."
              disabled={busy}
              style={{
                flex: 1, padding: '10px 14px', fontSize: 14, borderRadius: 10,
                border: `1px solid ${theme.border}`, background: theme.surface,
                color: theme.text, outline: 'none',
              }}
            />
            <button
              onClick={handleSend}
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

        <VoiceControls
          micOn={micOn}
          micBlocked={micBlocked}
          micBusy={micBusy}
          onToggleMic={toggleMic}
        />
      </div>
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

  const handleAuth = useCallback((u: UserProfile, token: string) => {
    setUser(u)
    setAccessToken(token)
    localStorage.setItem('finance_user', JSON.stringify(u))
    localStorage.setItem('finance_token', token)
  }, [])

  const handleLogout = useCallback(() => {
    setUser(null)
    setAccessToken(null)
    setLivekitToken(null)
    localStorage.removeItem('finance_user')
    localStorage.removeItem('finance_token')
  }, [])

  const connectGuest = useCallback(async () => {
    setConnecting(true)
    setError(null)
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
      setLivekitToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      setConnecting(false)
    }
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
        const body = await res.json()
        throw new Error(body.detail || `Token request failed: ${res.status}`)
      }
      const data: TokenResponse = await res.json()
      setLivekitToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      setConnecting(false)
    }
  }, [accessToken, handleLogout])

  const handleDisconnect = useCallback(() => {
    setLivekitToken(null)
    setServerUrl('')
    setConnecting(false)
  }, [])

  if (!user && !guestMode) {
    return <AuthPage onAuth={handleAuth} onGuest={() => { setGuestMode(true); connectGuest() }} />
  }

  if (livekitToken && serverUrl) {
    return (
      <LiveKitRoom
        token={livekitToken}
        serverUrl={serverUrl}
        connect={true}
        audio={true}
        video={false}
        onError={() => {}}
        onDisconnected={() => { handleDisconnect() }}
      >
        <RoomAudioRenderer />
        <RoomView />
      </LiveKitRoom>
    )
  }

  return (
    <div style={{ padding: 48, maxWidth: 500, margin: '0 auto', textAlign: 'center', color: theme.text }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>Finance Advisor</h1>
      <p style={{ color: theme.textDim, marginBottom: 24, fontSize: 14 }}>
        {guestMode ? 'Guest mode' : <>Signed in as <strong>{user!.display_name}</strong></>}
      </p>
      {error && <p style={{ color: theme.error, marginBottom: 16, fontSize: 13 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button
          onClick={connect}
          disabled={connecting}
          style={{
            padding: '12px 32px', fontSize: 16, fontWeight: 500,
            borderRadius: 8, border: 'none',
            background: connecting ? theme.surface2 : theme.accent,
            color: '#fff', cursor: connecting ? 'not-allowed' : 'pointer',
          }}
        >
          {connecting ? 'Connecting...' : 'Start Conversation'}
        </button>
      </div>
      <div style={{ marginTop: 16 }}>
        <button
          onClick={handleLogout}
          style={{
            padding: '8px 16px', fontSize: 13, fontWeight: 500,
            borderRadius: 6, border: `1px solid ${theme.border}`,
            background: 'transparent', color: theme.textDim, cursor: 'pointer',
          }}
        >
          {guestMode ? 'Go Back' : 'Sign Out'}
        </button>
      </div>
    </div>
  )
}

export default App

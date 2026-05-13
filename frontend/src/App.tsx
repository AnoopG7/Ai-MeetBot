import { useState, useCallback, useEffect, useRef } from 'react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useLocalParticipant,
} from '@livekit/components-react'
import { RoomEvent, type RemoteAudioTrack, type Participant } from 'livekit-client'
import { theme } from './theme'
import { useChat } from './hooks/useChat'
import { useTranscriptions } from './hooks/useTranscriptions'
import { CameraView } from './components/CameraView'
import { ChatList } from './components/ChatList'
import { VoiceControls } from './components/VoiceControls'
import { AuthPage } from './components/AuthPage'
import type { UserProfile } from './components/AuthPage'
import type { AgentState } from './components/AgentAvatar'

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
  const [layoutMode, setLayoutMode] = useState<'videocall' | 'chat'>('videocall')
  const [agentState, setAgentState] = useState<AgentState>('idle')
  const agentStateRef = useRef<AgentState>('idle')

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
    if (localParticipant) {
      // Always ensure mic is OFF on mount - user must click button to enable
      localParticipant.setMicrophoneEnabled(false).catch(() => {})
    }
  }, [localParticipant])

  useEffect(() => {
    applyMute(muted)
    const onTrackSubscribed = () => { applyMute(mutedRef.current) }
    room.on('trackSubscribed', onTrackSubscribed)
    return () => { room.off('trackSubscribed', onTrackSubscribed) }
  }, [muted, room, applyMute])

  useEffect(() => {
    let thinkingTimer: ReturnType<typeof setTimeout>
    const onActiveSpeakers = (speakers: Participant[]) => {
      const localSpeaking = speakers.find(p => p.isLocal)
      const remoteSpeaking = speakers.find(p => !p.isLocal)
      if (localSpeaking) {
        clearTimeout(thinkingTimer)
        setAgentState('listening')
        agentStateRef.current = 'listening'
      } else if (remoteSpeaking) {
        clearTimeout(thinkingTimer)
        setAgentState('speaking')
        agentStateRef.current = 'speaking'
      } else {
        if (agentStateRef.current === 'listening') {
          setAgentState('thinking')
          agentStateRef.current = 'thinking'
          thinkingTimer = setTimeout(() => {
            setAgentState((s) => {
              agentStateRef.current = s === 'thinking' ? 'idle' : s
              return agentStateRef.current
            })
          }, 2000)
        } else if (agentStateRef.current === 'speaking') {
          setAgentState('thinking')
          agentStateRef.current = 'thinking'
          thinkingTimer = setTimeout(() => {
            setAgentState((s) => {
              agentStateRef.current = s === 'thinking' ? 'idle' : s
              return agentStateRef.current
            })
          }, 1500)
        }
      }
    }
    room.on(RoomEvent.ActiveSpeakersChanged, onActiveSpeakers)
    return () => { room.off(RoomEvent.ActiveSpeakersChanged, onActiveSpeakers); clearTimeout(thinkingTimer) }
  }, [room])

  function cleanToolCall(text: string): string {
    return text.replace(/<function=[\s\S]*?<\/function>/g, '').trim()
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
      const newState = !micOn
      await localParticipant.setMicrophoneEnabled(newState)
      setMicOn(newState)
    } catch (err) {
      console.error('Mic toggle error:', err)
      setMicBlocked(true)
      setMicOn(false)
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

  const isVideocall = layoutMode === 'videocall'

  const header = (
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

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button
          onClick={() => setLayoutMode(isVideocall ? 'chat' : 'videocall')}
          title={isVideocall ? 'Switch to chat view' : 'Switch to video call view'}
          style={{
            padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
            border: `1px solid ${theme.border}`, background: 'transparent',
            color: theme.textDim, cursor: 'pointer',
          }}
        >
          {isVideocall ? '☰ Chat' : '📹 Call'}
        </button>
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
    </div>
  )

  if (isVideocall) {
    return (
      <div style={{
        height: '100vh', display: 'flex', flexDirection: 'column',
        background: theme.bg, color: theme.text,
      }}>
        {header}
        <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
          <CameraView
            participant={localParticipant?.identity}
            mode="videocall"
            agentState={agentState}
            micOn={micOn}
            micBusy={micBusy}
            onToggleMic={toggleMic}
          />
          <div style={{
            width: 380, flexShrink: 0, display: 'flex', flexDirection: 'column',
            borderLeft: `1px solid ${theme.border}`,
          }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <ChatList messages={messages} busy={busy} />
            </div>
            <div style={{
              display: 'flex', gap: 8, padding: '12px 16px',
              borderTop: `1px solid ${theme.border}`,
              flexShrink: 0,
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
        </div>
      </div>
    )
  }

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      background: theme.bg, color: theme.text,
    }}>
      {header}
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
        <CameraView participant={localParticipant?.identity} mode="sidebar" agentState={agentState} />
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
        audio={{ autoGainControl: true, noiseSuppression: true, echoCancellation: true }}
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

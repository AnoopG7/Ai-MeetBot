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

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [serverUrl, setServerUrl] = useState<string>('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const connect = useCallback(async () => {
    setConnecting(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/livekit/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: DEFAULT_ROOM }),
      })
      if (!res.ok) {
        throw new Error(`Token request failed: ${res.status} ${res.statusText}`)
      }
      const data: TokenResponse = await res.json()
      setToken(data.token)
      setServerUrl(data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
    } finally {
      setConnecting(false)
    }
  }, [])

  if (token && serverUrl) {
    return (
      <LiveKitRoom
        token={token}
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
      <h1>Finance Advisor</h1>
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
          padding: '12px 32px',
          fontSize: 16,
          borderRadius: 8,
          border: 'none',
          background: '#0066cc',
          color: '#fff',
          cursor: connecting ? 'not-allowed' : 'pointer',
        }}
      >
        {connecting ? 'Connecting...' : 'Start Conversation'}
      </button>
    </div>
  )
}

export default App

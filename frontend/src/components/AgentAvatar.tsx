import { useEffect, useState } from 'react'

export type AgentState = 'idle' | 'listening' | 'thinking' | 'speaking'

export function AgentAvatar({ state }: { state: AgentState }) {
  const [pulse, setPulse] = useState(false)

  useEffect(() => {
    if (state === 'speaking' || state === 'thinking') {
      const t = setInterval(() => setPulse((p) => !p), state === 'speaking' ? 600 : 900)
      return () => { clearInterval(t); setPulse(false) }
    }
    setPulse(false)
  }, [state])

  const label = { idle: 'Agent', listening: 'Listening', thinking: 'Thinking...', speaking: 'Speaking' }[state]
  const ringColor = {
    idle: '#555',
    listening: '#22aa66',
    thinking: '#f0a030',
    speaking: '#00dd88',
  }[state]

  const size = pulse && state === 'speaking' ? 76 : state === 'thinking' && pulse ? 70 : 64
  const glow = state === 'speaking' ? `0 0 ${pulse ? 20 : 8}px ${ringColor}` : 'none'

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
    }}>
      <div style={{
        width: size, height: size, borderRadius: '50%',
        background: `radial-gradient(circle at 35% 35%, #2a2a3a, #1a1a2a)`,
        border: `2px solid ${ringColor}`,
        boxShadow: glow,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'width 0.3s, height 0.3s, box-shadow 0.3s',
        position: 'relative',
      }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: '#ddd', letterSpacing: 1 }}>AI</span>
      </div>
      <span style={{
        fontSize: 11, color: ringColor, fontWeight: 600,
        transition: 'color 0.3s',
      }}>
        {label}
      </span>
    </div>
  )
}

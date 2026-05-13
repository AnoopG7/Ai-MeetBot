import { theme } from '../theme'

interface ChatMessageProps {
  role: 'user' | 'agent'
  text: string
  isFinal: boolean
  source: 'voice' | 'text'
}

export function ChatMessage({ role, text, isFinal, source }: ChatMessageProps) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: role === 'user' ? 'flex-end' : 'flex-start',
      marginBottom: 6,
      opacity: isFinal ? 1 : 0.6,
      transition: 'opacity 0.15s',
    }}>
      <div style={{
        maxWidth: '75%',
        padding: '10px 16px',
        borderRadius: 16,
        fontSize: 14,
        lineHeight: 1.55,
        background: role === 'user' ? theme.accent : theme.surface2,
        color: role === 'user' ? '#fff' : theme.text,
        borderBottomRightRadius: role === 'user' ? 4 : 16,
        borderBottomLeftRadius: role === 'user' ? 16 : 4,
        position: 'relative',
      }}>
        {text}
        {!isFinal && (
          <span style={{ opacity: 0.5, marginLeft: 2 }}>▎</span>
        )}
        {role === 'agent' && source === 'voice' && (
          <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.5 }}>🔊</span>
        )}
      </div>
    </div>
  )
}

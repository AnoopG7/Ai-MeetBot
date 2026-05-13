import { useRef, useEffect } from 'react'
import { ChatMessage } from './ChatMessage'
import { theme } from '../theme'
import type { ChatMessage as ChatMessageType } from '../hooks/useChat'

interface ChatListProps {
  messages: ChatMessageType[]
  busy: boolean
}

export function ChatList({ messages, busy }: ChatListProps) {
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div ref={listRef} style={{
      flex: 1,
      overflowY: 'auto',
      padding: '16px 20px',
    }}>
      {messages.length === 0 && (
        <div style={{
          color: theme.textDim,
          fontSize: 13,
          textAlign: 'center',
          marginTop: 48,
          lineHeight: 1.8,
        }}>
          Enable your mic and speak, or type below.
          <br />
          Responses will appear here and be spoken aloud.
        </div>
      )}
      {messages.map(m => (
        <ChatMessage
          key={m.id}
          role={m.role}
          text={m.text}
          isFinal={m.isFinal}
          source={m.source}
        />
      ))}
      {busy && (
        <div style={{ display: 'flex', gap: 5, padding: '12px 4px' }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: theme.textDim, animation: 'none',
          }} />
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: theme.textDim, animation: 'none',
          }} />
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: theme.textDim, animation: 'none',
          }} />
        </div>
      )}
    </div>
  )
}

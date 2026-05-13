import { useState, useCallback, useRef } from 'react'
import { useRoomContext } from '@livekit/components-react'

export interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  text: string
  isFinal: boolean
  source: 'voice' | 'text'
  timestamp: number
}

let nextId = 1

export function useChat() {
  const room = useRoomContext()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)

  const addMessage = useCallback((role: 'user' | 'agent', text: string, isFinal = true, source: 'voice' | 'text' = 'text') => {
    const id = String(nextId++)
    setMessages(prev => [...prev, { id, role, text, isFinal, source, timestamp: Date.now() }])
    return id
  }, [])

  const upsertMessage = useCallback((role: 'user' | 'agent', segmentId: string, text: string, isFinal: boolean) => {
    setMessages(prev => {
      const idx = prev.findIndex(m => m.id === segmentId)
      if (idx !== -1) {
        const updated = [...prev]
        updated[idx] = { ...updated[idx], text, isFinal }
        return updated
      }
      const id = segmentId
      return [...prev, { id, role, text, isFinal, source: 'voice', timestamp: Date.now() }]
    })
  }, [])

  const sendText = useCallback(async (text: string): Promise<string | null> => {
    if (!text.trim() || busyRef.current) return null
    addMessage('user', text.trim(), true, 'text')
    busyRef.current = true
    setBusy(true)
    try {
      const encoder = new TextEncoder()
      await room.localParticipant.publishData(
        encoder.encode(text.trim()),
        { reliable: true, topic: 'chat' }
      )
      return null
    } catch {
      busyRef.current = false
      setBusy(false)
      return null
    }
  }, [addMessage, room])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, busy, sendText, upsertMessage, clearMessages }
}

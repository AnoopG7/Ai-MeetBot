import { useState, useCallback, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
      const r = await fetch(`${API_URL}/api/debug/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim() }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      addMessage('agent', d.response, true, 'text')
      return d.response
    } catch (e) {
      const err = e instanceof Error ? e.message : 'Unknown error'
      addMessage('agent', `Error: ${err}`, true, 'text')
      return null
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }, [addMessage])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, busy, sendText, upsertMessage, clearMessages }
}

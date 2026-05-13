import { useEffect, useCallback, useRef } from 'react'
import type { Room, Participant, TranscriptionSegment } from 'livekit-client'

export interface TranscriptionEvent {
  segmentId: string
  text: string
  participantIdentity: string
  isFinal: boolean
}

type TranscriptionHandler = (evt: TranscriptionEvent) => void

export function useTranscriptions(room: Room | null, onTranscription: TranscriptionHandler) {
  const handlerRef = useRef(onTranscription)
  handlerRef.current = onTranscription

  const handleEvent = useCallback((segments: TranscriptionSegment[], participant?: Participant) => {
    const identity = participant?.identity ?? 'agent'
    for (const s of segments) {
      handlerRef.current({
        segmentId: s.id,
        text: s.text,
        participantIdentity: identity,
        isFinal: s.final,
      })
    }
  }, [])

  useEffect(() => {
    if (!room) return
    room.on('transcriptionReceived', handleEvent)
    return () => { room.off('transcriptionReceived', handleEvent) }
  }, [room, handleEvent])
}

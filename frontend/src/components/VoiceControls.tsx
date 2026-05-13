import { BarVisualizer } from '@livekit/components-react'
import { theme } from '../theme'

interface VoiceControlsProps {
  micOn: boolean
  micBlocked: boolean
  micBusy: boolean
  onToggleMic: () => void
}

export function VoiceControls({ micOn, micBlocked, micBusy, onToggleMic }: VoiceControlsProps) {
  const barState = micOn && !micBlocked ? 'listening' : 'idle'

  return (
    <div style={{
      width: 220,
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 20,
      padding: 24,
      borderLeft: `1px solid ${theme.border}`,
    }}>
      <div style={{
        width: 140, height: 64, borderRadius: 12,
        background: theme.surface2,
        display: 'flex', alignItems: 'center',
        justifyContent: 'center', overflow: 'hidden',
      }}>
        <BarVisualizer
          state={barState}
          barCount={7}
          options={{ minHeight: 12, maxHeight: 56 }}
          style={{ width: 120, height: 48 }}
        />
      </div>

      <button
        onClick={onToggleMic}
        disabled={micBusy}
        title={micBlocked ? 'Mic blocked — click to retry' : micOn ? 'Mute microphone' : 'Enable microphone'}
        style={{
          width: 72, height: 72, borderRadius: '50%', border: 'none',
          background: !micOn ? theme.surface2 : micBlocked ? theme.error : theme.green,
          color: '#fff', fontSize: 28, cursor: micBusy ? 'wait' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.12s',
          opacity: micBusy ? 0.5 : 1,
        }}
      >
        {micBlocked ? '🚫' : micOn ? '🎤' : '🎙️'}
      </button>

      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 12, color: theme.textDim }}>
          {micBlocked
            ? 'Microphone blocked'
            : !micOn
              ? 'Mic off — tap to speak'
              : 'Listening — speak freely'}
        </div>
        {micBlocked && (
          <div style={{ fontSize: 11, color: theme.error, marginTop: 4 }}>
            Allow mic access in browser
          </div>
        )}
      </div>
    </div>
  )
}

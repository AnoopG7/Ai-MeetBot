import { useCallback, useEffect, useRef, useState } from 'react'
import { theme } from '../theme'
import { AgentAvatar } from './AgentAvatar'

interface FaceInfo {
  x: number; y: number; w: number; h: number
  left_eye: boolean; right_eye: boolean
  smile: boolean; mouth_open: boolean
  engagement: number
}

interface VisualState {
  face_detected: boolean
  face_count: number
  face_x: number; face_y: number; face_w: number; face_h: number
  gaze: string; head_pose: string
  engagement: number
  smiling: boolean; mouth_open: boolean
  left_eye: boolean; right_eye: boolean
  eye_count: number; blink_rate: number
  nod_count: number; looking_away_sec: number
  pitch: number; yaw: number; roll: number
  faces: FaceInfo[]
}

type AgentState = 'idle' | 'listening' | 'thinking' | 'speaking'

interface CameraViewProps {
  participant?: string
  mode: 'sidebar' | 'videocall'
  agentState: AgentState
  onToggleCamera?: (on: boolean) => void
  micOn?: boolean
  micBusy?: boolean
  onToggleMic?: () => void
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FPS = 5
const INTERVAL = 1000 / FPS

export function CameraView({ participant, mode, agentState, onToggleCamera, micOn, micBusy, onToggleMic }: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const capRef = useRef<HTMLCanvasElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [on, setOn] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [visual, setVisual] = useState<VisualState | null>(null)

  useEffect(() => { onToggleCamera?.(on) }, [on, onToggleCamera])

  const sendFrame = useCallback(() => {
    const video = videoRef.current
    const cap = capRef.current
    const ws = wsRef.current
    if (!video || !cap || !ws || ws.readyState !== WebSocket.OPEN) return
    cap.width = 640; cap.height = 480
    const ctx = cap.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, 640, 480)
    cap.toBlob((blob) => { if (blob) ws.send(blob) }, 'image/jpeg', 0.7)
  }, [])

  const drawOverlay = useCallback((v: VisualState) => {
    const c = overlayRef.current
    if (!c) return
    const cw = c.width, ch = c.height
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, cw, ch)
    if (!v.face_detected) return
    for (const f of v.faces) {
      const bx = f.x * cw - (f.w * cw) / 2
      const by = f.y * ch - (f.h * ch) / 2
      const bw = f.w * cw
      const bh = f.h * ch
      ctx.strokeStyle = f.left_eye && f.right_eye ? '#00ff88' : '#ff8844'
      ctx.lineWidth = f.engagement > 0.6 ? 2.5 : 1.5
      ctx.strokeRect(bx, by, bw, bh)
      if (f.smile) {
        ctx.fillStyle = '#ffdd00'; ctx.font = '16px sans-serif'
        ctx.fillText('😊', bx + 4, by + 18)
      }
      if (f.mouth_open) {
        ctx.fillStyle = '#ff66aa'; ctx.font = '16px sans-serif'
        ctx.fillText('👄', bx + bw - 24, by + 18)
      }
    }
  }, [])

  const start = useCallback(async () => {
    setBlocked(false)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, frameRate: 15 } })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      const pid = participant || 'unknown'
      const protocol = API_URL.startsWith('https') ? 'wss' : 'ws'
      const wsUrl = `${protocol}://${API_URL.replace(/^https?:\/\//, '')}/api/vision/ws?participant=${pid}`
      const ws = new WebSocket(wsUrl)
      ws.onmessage = (evt) => {
        try { const v = JSON.parse(evt.data) as VisualState; setVisual(v); drawOverlay(v) }
        catch { /* ignore */ }
      }
      wsRef.current = ws
      intervalRef.current = setInterval(sendFrame, INTERVAL)
      setOn(true)
    } catch { setBlocked(true) }
  }, [participant, sendFrame, drawOverlay])

  const stop = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (wsRef.current) wsRef.current.close()
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop())
    setOn(false); setVisual(null)
  }, [])

  useEffect(() => stop, [stop])

  const awayLong = !!(visual && visual.face_detected && visual.looking_away_sec > 3)

  if (mode === 'sidebar') {
    return (
      <div style={{ width: 240, borderLeft: `1px solid ${theme.border}`, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: theme.textDim }}>Camera</span>
          <CamButton on={on} blocked={blocked} onStart={start} onStop={stop} />
        </div>
        <div style={{ position: 'relative', width: 240, height: 180, background: theme.surface2, overflow: 'hidden' }}>
          <video ref={videoRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover', display: on ? 'block' : 'none' }} />
          <canvas ref={overlayRef} width={240} height={180} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: on ? 'block' : 'none' }} />
          {!on && !blocked && <Placeholder text="Camera off" />}
          <canvas ref={capRef} style={{ display: 'none' }} />
        </div>
        {on && visual && <VisualPanel visual={visual} awayLong={awayLong} />}
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: '#0a0a12', position: 'relative' }}>
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <video ref={videoRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'contain', display: on ? 'block' : 'none' }} />
        <canvas ref={overlayRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', display: on ? 'block' : 'none' }} />
        {!on && !blocked && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
            <AgentAvatar state={agentState} />
            <Placeholder text="Camera off" />
          </div>
        )}
        {on && !visual?.face_detected && visual !== null && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
            <AgentAvatar state={agentState} />
            <span style={{ fontSize: 13, color: theme.textDim }}>No face detected</span>
          </div>
        )}
        <canvas ref={capRef} style={{ display: 'none' }} />
      </div>

      {on && visual && (
        <div style={{
          position: 'absolute', top: 12, left: 12,
          background: 'rgba(0,0,0,0.6)', borderRadius: 8, padding: '6px 10px',
          display: 'flex', gap: 10, fontSize: 11, backdropFilter: 'blur(4px)',
        }}>
          <span style={{ color: visual.face_detected ? theme.green : theme.textDim }}>
            {visual.face_detected ? `👤 ${visual.face_count}` : '🚫'}
          </span>
          {visual.face_detected && (
            <>
              <span style={{ color: visual.smiling ? '#ffdd00' : theme.textDim }}>😊{visual.smiling ? ' smile' : ''}</span>
              <span style={{ color: visual.mouth_open ? '#ff66aa' : theme.textDim }}>👄{visual.mouth_open ? ' open' : ''}</span>
              <span style={{ color: visual.gaze === 'at_camera' ? '#00ff88' : theme.textDim }}>👁 {visual.gaze}</span>
              <span style={{ color: theme.accent }}>⚡{Math.round(visual.engagement * 100)}%</span>
            </>
          )}
        </div>
      )}

      <div style={{
        height: 80, borderTop: `1px solid ${theme.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20,
        padding: '0 20px', flexShrink: 0,
      }}>
        <CamButton on={on} blocked={blocked} onStart={start} onStop={stop} large />
        <MicButton on={!!micOn} blocked={false} busy={!!micBusy} onToggle={onToggleMic || (() => {})} />
        <AgentAvatar state={agentState} />
        {on && visual && (
          <div style={{ display: 'flex', gap: 16, fontSize: 11, color: theme.textDim }}>
            <EngageBadge value={visual.engagement} />
            {awayLong && <span style={{ color: theme.error, fontWeight: 600 }}>⚠ Away {visual.looking_away_sec.toFixed(0)}s</span>}
            {visual.nod_count > 0 && <span>↕ {visual.nod_count}</span>}
          </div>
        )}
      </div>
    </div>
  )
}

function MicButton({ on, blocked, busy, onToggle }: { on: boolean; blocked: boolean; busy: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      disabled={busy}
      title={blocked ? 'Mic blocked' : on ? 'Mute microphone' : 'Enable microphone'}
      style={{
        width: 44, height: 44, borderRadius: '50%', border: 'none',
        background: !on ? theme.surface2 : blocked ? theme.error : theme.green,
        color: '#fff', fontSize: 18, cursor: busy ? 'wait' : 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.12s', opacity: busy ? 0.5 : 1,
      }}
    >
      {blocked ? '🚫' : on ? '🎤' : '🎙️'}
    </button>
  )
}

function CamButton({ on, blocked, onStart, onStop, large }: { on: boolean; blocked: boolean; onStart: () => void; onStop: () => void; large?: boolean }) {
  const s = large ? { px: 14, fs: 12 } : { px: 10, fs: 11 }
  return (
    <button
      onClick={on ? onStop : onStart}
      disabled={blocked}
      style={{
        padding: `${s.px / 2}px ${s.px}px`, fontSize: s.fs, borderRadius: 8,
        border: `1px solid ${on ? theme.error : theme.border}`,
        background: on ? theme.error + '22' : 'transparent',
        color: on ? theme.error : theme.textDim, cursor: 'pointer',
        fontWeight: 500,
      }}
    >
      {blocked ? 'Blocked' : on ? 'Stop Cam' : 'Start Cam'}
    </button>
  )
}

function Placeholder({ text }: { text: string }) {
  return <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: theme.textDim }}>{text}</div>
}

function EngageBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = value > 0.6 ? theme.green : value > 0.3 ? '#f0a030' : theme.error
  return <span style={{ color }}>Engage {pct}%</span>
}

function VisualPanel({ visual, awayLong }: { visual: VisualState; awayLong: boolean }) {
  return (
    <div style={{ padding: '8px 12px', fontSize: 11, lineHeight: 1.7, color: theme.textDim }}>
      <EngageBadge value={visual.engagement} />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
        <span>Gaze: <b style={{ color: theme.text }}>{visual.gaze}</b></span>
        <span>Pose: <b style={{ color: theme.text }}>{visual.head_pose}</b></span>
        <span>Eyes: <b style={{ color: visual.eye_count === 2 ? theme.green : theme.error }}>{visual.eye_count}</b></span>
      </div>
      <div style={{ display: 'flex', gap: 8, fontSize: 10 }}>
        <span>😊 {visual.smiling ? 'smile' : '—'}</span>
        <span>👄 {visual.mouth_open ? 'open' : '—'}</span>
        <span>💫 {visual.blink_rate.toFixed(1)}/s</span>
        <span>↕ {visual.nod_count}</span>
      </div>
      {awayLong && <div style={{ color: theme.error, fontWeight: 600, marginTop: 4 }}>⚠ Away {visual.looking_away_sec.toFixed(0)}s</div>}
    </div>
  )
}

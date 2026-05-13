import { useCallback, useEffect, useRef, useState } from 'react'
import { theme } from '../theme'

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

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FPS = 5
const INTERVAL = 1000 / FPS

function EngagementBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = value > 0.6 ? theme.green : value > 0.3 ? '#f0a030' : theme.error
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ width: 50, fontSize: 11, color: theme.textDim }}>Engage</span>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: theme.surface2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ width: 28, fontSize: 10, color, fontWeight: 600, textAlign: 'right' }}>{pct}%</span>
    </div>
  )
}

export function CameraView({ participant }: { participant?: string }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const capRef = useRef<HTMLCanvasElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [on, setOn] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [visual, setVisual] = useState<VisualState | null>(null)

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
      const high = f.engagement > 0.6
      ctx.strokeStyle = f.left_eye && f.right_eye ? '#00ff88' : '#ff8844'
      ctx.lineWidth = high ? 2.5 : 1.5
      ctx.strokeRect(bx, by, bw, bh)
      if (f.smile) {
        ctx.fillStyle = '#ffdd00'
        ctx.font = '14px sans-serif'
        ctx.fillText('😊', bx + 4, by + 16)
      }
      if (f.mouth_open) {
        ctx.fillStyle = '#ff66aa'
        ctx.font = '14px sans-serif'
        ctx.fillText('👄', bx + bw - 20, by + 16)
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

  const awayLong = visual && visual.face_detected && visual.looking_away_sec > 3

  return (
    <div style={{
      width: 240, borderLeft: `1px solid ${theme.border}`,
      display: 'flex', flexDirection: 'column', flexShrink: 0,
      transition: 'box-shadow 0.3s',
      boxShadow: awayLong ? `inset 0 0 0 2px ${theme.error}` : 'none',
    }}>
      <div style={{ padding: '8px 12px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: theme.textDim }}>Camera</span>
        <button onClick={on ? stop : start} disabled={blocked} style={{
          padding: '4px 10px', fontSize: 11, borderRadius: 6,
          border: `1px solid ${on ? theme.error : theme.border}`,
          background: on ? theme.error + '22' : 'transparent',
          color: on ? theme.error : theme.textDim, cursor: 'pointer',
        }}>
          {blocked ? 'Blocked' : on ? 'Stop' : 'Start'}
        </button>
      </div>

      <div style={{ position: 'relative', width: 240, height: 180, background: theme.surface2, overflow: 'hidden' }}>
        <video ref={videoRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover', display: on ? 'block' : 'none' }} />
        <canvas ref={overlayRef} width={240} height={180} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: on ? 'block' : 'none' }} />
        {!on && !blocked && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: theme.textDim }}>Camera off</div>}
        <canvas ref={capRef} style={{ display: 'none' }} />
      </div>

      {on && visual && (
        <div style={{ padding: '8px 12px', fontSize: 11, lineHeight: 1.7, color: theme.textDim }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: visual.face_detected ? theme.green : theme.error }} />
            {visual.face_detected ? `${visual.face_count} face${visual.face_count > 1 ? 's' : ''}` : 'No face'}
          </div>

          {visual.face_detected && (
            <>
              <EngagementBar value={visual.engagement} />

              <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                <Indicator label="Gaze" value={visual.gaze} color={visual.gaze === 'at_camera' ? theme.green : theme.error} />
                <Indicator label="Pose" value={visual.head_pose} color={theme.text} />
                <Indicator label="Eyes" value={visual.eye_count === 2 ? '✓✓' : visual.eye_count === 1 ? '✓' : '--'} color={visual.eye_count === 2 ? theme.green : theme.error} />
              </div>

              <div style={{ display: 'flex', gap: 12, marginTop: 2 }}>
                <MiniBadge label="😊 smile" active={visual.smiling} />
                <MiniBadge label="👄 mouth" active={visual.mouth_open} />
                <MiniBadge label="↕ nod" value={String(visual.nod_count)} />
                <MiniBadge label="👁 blink" value={`${visual.blink_rate.toFixed(1)}/s`} />
              </div>

              {awayLong && (
                <div style={{ color: theme.error, fontWeight: 600, marginTop: 4, animation: 'pulse 1s infinite' }}>
                  ⚠ Away {visual.looking_away_sec.toFixed(0)}s
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function Indicator({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      <span style={{ color: theme.textDim }}>{label}:</span>
      <b style={{ color, fontSize: 12 }}>{value}</b>
    </div>
  )
}

function MiniBadge({ label, active, value }: { label: string; active?: boolean; value?: string }) {
  const lit = value !== undefined || active === true
  return (
    <span title={label} style={{
      fontSize: 10, padding: '1px 6px', borderRadius: 4,
      background: lit ? theme.accent + '22' : 'transparent',
      color: lit ? theme.accent : theme.textDim,
    }}>
      {value !== undefined ? `${label.split(' ').pop()} ${value}` : label}
    </span>
  )
}

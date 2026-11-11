import { useEffect, useState, useRef, memo } from 'react'
import { useTelemetry } from '../hooks/useTelemetry'

interface Corner {
  number?: number
  letter?: string
  canvas_x: number
  canvas_y: number
}

interface CanvasData {
  width: number
  height: number
  centerline: Array<[number, number]>
  corners: Corner[]
}

interface SessionInfo {
  circuit_key: number
  year: number
  circuit_short_name: string
  session_type: string
}

interface TrackMapProps {
  sessionInfo?: SessionInfo
}

const DRIVER_COLORS: Record<number, string> = {
  1: '#1E41FF', 11: '#1E41FF', // Red Bull
  16: '#E8002D', 55: '#E8002D', // Ferrari
  63: '#27F4D2', 44: '#27F4D2', // Mercedes
  4: '#FF8000', 81: '#FF8000', // McLaren
  14: '#229971', 18: '#229971', // Aston Martin
  10: '#0093CC', 31: '#0093CC', // Alpine
  23: '#37BEDD', 2: '#37BEDD', // Williams
  3: '#6692FF', 22: '#6692FF', // RB
  77: '#52E252', 24: '#52E252', // Stake / Sauber
  20: '#B6BABD', 27: '#B6BABD', // Haas
}

const TrackMap = memo(function TrackMap({ sessionInfo }: TrackMapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null)
  const [carPositions, setCarPositions] = useState<Record<number, { x: number; y: number }>>({})
  const { telemetry } = useTelemetry()

  // 실시간 텔레메트리 수신 시 위치 저장
  useEffect(() => {
    if (telemetry && telemetry.driver_number && telemetry.x !== undefined && telemetry.y !== undefined) {
      setCarPositions(prev => ({
        ...prev,
        [telemetry.driver_number]: { x: telemetry.x!, y: telemetry.y! }
      }))
    }
  }, [telemetry])

  // 트랙 Canvas 좌표 Fetch (세션 인식 API 사용)
  useEffect(() => {
    let active = true
    async function loadTrack() {
      if (!sessionInfo) return
      try {
        const { year, circuit_short_name: gp, session_type } = sessionInfo
        const encodedGp = encodeURIComponent(gp)
        const res = await fetch(`/api/session/${year}/${encodedGp}/${session_type}/track`)
        if (res.ok) {
          const data = await res.json()
          if (active && data.success && data.canvas) {
            setCanvasData(data.canvas)
          }
        }
      } catch (err) {
        console.error('Failed to fetch track canvas data', err)
      }
    }
    loadTrack()
    return () => { active = false }
  }, [sessionInfo])

  // Canvas 렌더링
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height

    ctx.fillStyle = '#0d1117'
    ctx.fillRect(0, 0, width, height)

    if (!canvasData || !canvasData.centerline || canvasData.centerline.length === 0) {
      ctx.fillStyle = '#8b949e'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Loading track layout...', width / 2, height / 2)
      return
    }

    // 1. 트랙 라인
    ctx.beginPath()
    ctx.strokeStyle = '#30363d'
    ctx.lineWidth = 12
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    canvasData.centerline.forEach(([x, y], idx) => {
      if (idx === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    ctx.beginPath()
    ctx.strokeStyle = '#58a6ff'
    ctx.lineWidth = 4
    canvasData.centerline.forEach(([x, y], idx) => {
      if (idx === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // 2. 코너 마커
    if (canvasData.corners) {
      canvasData.corners.forEach(corner => {
        ctx.beginPath()
        ctx.arc(corner.canvas_x, corner.canvas_y, 4, 0, 2 * Math.PI)
        ctx.fillStyle = '#f85149'
        ctx.fill()

        if (corner.number) {
          ctx.fillStyle = '#8b949e'
          ctx.font = '10px sans-serif'
          ctx.textAlign = 'center'
          ctx.fillText(`T${corner.number}`, corner.canvas_x, corner.canvas_y - 8)
        }
      })
    }

    // 3. 실시간 차량 위치 오버레이
    Object.entries(carPositions).forEach(([driverNumStr, pos]) => {
      const driverNum = parseInt(driverNumStr)
      const color = DRIVER_COLORS[driverNum] || '#e6edf3'

      ctx.beginPath()
      ctx.arc(pos.x, pos.y, 8, 0, 2 * Math.PI)
      ctx.fillStyle = color
      ctx.fill()
      ctx.lineWidth = 2
      ctx.strokeStyle = '#ffffff'
      ctx.stroke()

      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 9px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(`${driverNum}`, pos.x, pos.y)
    })

  }, [canvasData, carPositions])

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0d1117' }}>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{ maxWidth: '100%', maxHeight: '100%', border: '1px solid #30363d', borderRadius: 8 }}
      />
    </div>
  )
})

export default TrackMap

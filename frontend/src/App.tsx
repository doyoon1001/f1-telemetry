import { useState } from 'react'
import TrackMap from './components/TrackMap'
import TelemetryPanel from './components/TelemetryPanel'
import DriverList from './components/DriverList'
import { useTelemetry } from './hooks/useTelemetry'

interface SessionInfo {
  circuit_key: number
  year: number
  circuit_short_name: string
  session_type: string
}

const GP_OPTIONS = [
  { value: 'Bahrain', label: 'Bahrain', circuitKey: 1 },
  { value: 'Saudi Arabia', label: 'Saudi Arabia', circuitKey: 2 },
  { value: 'Australia', label: 'Australia', circuitKey: 3 },
  { value: 'Japan', label: 'Japan', circuitKey: 4 },
  { value: 'China', label: 'China', circuitKey: 5 },
  { value: 'Miami', label: 'Miami', circuitKey: 6 },
  { value: 'Emilia Romagna', label: 'Emilia Romagna', circuitKey: 7 },
  { value: 'Monaco', label: 'Monaco', circuitKey: 8 },
  { value: 'Canada', label: 'Canada', circuitKey: 9 },
  { value: 'Spain', label: 'Spain', circuitKey: 10 },
  { value: 'Austria', label: 'Austria', circuitKey: 11 },
  { value: 'Great Britain', label: 'Great Britain', circuitKey: 12 },
  { value: 'Hungary', label: 'Hungary', circuitKey: 13 },
  { value: 'Belgium', label: 'Belgium', circuitKey: 14 },
  { value: 'Netherlands', label: 'Netherlands', circuitKey: 15 },
  { value: 'Italy', label: 'Italy', circuitKey: 16 },
  { value: 'Azerbaijan', label: 'Azerbaijan', circuitKey: 17 },
  { value: 'Singapore', label: 'Singapore', circuitKey: 18 },
  { value: 'United States', label: 'United States', circuitKey: 19 },
  { value: 'Mexico', label: 'Mexico', circuitKey: 20 },
  { value: 'Brazil', label: 'Brazil', circuitKey: 21 },
  { value: 'Las Vegas', label: 'Las Vegas', circuitKey: 22 },
  { value: 'Qatar', label: 'Qatar', circuitKey: 23 },
  { value: 'Abu Dhabi', label: 'Abu Dhabi', circuitKey: 24 },
]

function App() {
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(() => {
    const saved = localStorage.getItem('f1_session')
    return saved ? JSON.parse(saved) : null
  })
  const { connected } = useTelemetry()

  const loadSession = async (year: number, gp: string, sessionType: string, circuitKey: number) => {
    try {
      const res = await fetch(`/api/session/load?year=${year}&gp=${gp}&session_type=${sessionType}`, {
        method: 'POST'
      })
      const data = await res.json()
      if (data.success) {
        const info = {
          ...data.session,
          circuit_key: circuitKey || data.session.circuit_key,
          year,
          circuit_short_name: gp,
          session_type: sessionType
        }
        setSessionInfo(info)
        localStorage.setItem('f1_session', JSON.stringify(info))
      }
    } catch (e) {
      console.error('Failed to load session:', e)
    }
  }

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh' }}>
      <div style={{ flex: 2, position: 'relative', minWidth: 0 }}>
        <div style={{ position: 'absolute', top: 16, left: 16, zIndex: 1000, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select
            onChange={(e) => {
              const opt = GP_OPTIONS.find(o => o.value === e.target.value)
              loadSession(2024, e.target.value, 'R', opt?.circuitKey || 0)
            }}
            style={{ padding: '8px 12px', background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border)', borderRadius: 8 }}
          >
            {GP_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
          <span style={{ color: connected ? '#4ade80' : '#f87171', fontSize: 14 }}>
            {connected ? '🟢 Live' : '🔴 Disconnected'}
          </span>
        </div>
        <TrackMap sessionInfo={sessionInfo || undefined} />
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 320, maxWidth: 400, borderLeft: '1px solid var(--border)' }}>
        <TelemetryPanel />
        <DriverList sessionInfo={sessionInfo} />
      </div>
    </div>
  )
}

export default App
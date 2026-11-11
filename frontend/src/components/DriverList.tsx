import { useEffect, useState } from 'react'

interface SessionInfo {
  year: number
  circuit_short_name: string
  session_type: string
  circuit_key: number
}

interface DriverSummary {
  driver_number: number
  driver_name?: string
  team_name?: string
  team_color?: string
  position?: number
  lap?: number
  tyre_compound?: string
}

interface DriverListProps {
  sessionInfo: SessionInfo | null
}

async function fetchDrivers(year: number, gp: string, sessionType: string) {
  try {
    const res = await fetch(`/api/session/${year}/${encodeURIComponent(gp)}/${sessionType}/drivers`)
    if (!res.ok) return []
    const data = await res.json()
    return data.drivers ?? []
  } catch {
    return []
  }
}

export default function DriverList({ sessionInfo }: DriverListProps) {
  const [drivers, setDrivers] = useState<DriverSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    if (!sessionInfo) {
      setDrivers([])
      setLoading(false)
      return
    }
    ;(async () => {
      setLoading(true)
      const data = await fetchDrivers(sessionInfo.year, sessionInfo.circuit_short_name, sessionInfo.session_type)
      if (mounted) {
        setDrivers(Array.isArray(data) ? data : [])
        setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [sessionInfo])

  return (
    <div style={{ flex: 1, overflowY: 'auto', borderTop: '1px solid var(--border)' }}>
      <div style={{ padding: 16 }}>
        <h3 style={{ margin: '0 0 12px 0' }}>Drivers</h3>
        {loading ? (
          <div style={{ color: 'var(--fg-secondary)' }}>Loading...</div>
        ) : drivers.length === 0 ? (
          <div style={{ color: 'var(--fg-secondary)' }}>No data</div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {drivers.map(d => (
              <div
                key={d.driver_number}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: 8,
                  borderRadius: 8,
                  background: 'var(--bg-secondary)',
                }}
              >
                <div style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: d.team_color ?? '#333',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                  fontSize: 12,
                  color: 'white'
                }}>
                  {d.driver_number}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {d.driver_name ?? `#${d.driver_number}`}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>
                    {d.team_name ?? ''} · {d.tyre_compound ?? ''}
                  </div>
                </div>
                <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>
                  P{d.position ?? '-'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
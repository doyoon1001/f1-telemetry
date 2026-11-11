import { useState, useEffect } from 'react'
import { useTelemetry } from '../hooks/useTelemetry'

function formatTime(seconds?: number) {
  if (!seconds || !isFinite(seconds)) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds - Math.floor(seconds)) * 1000)
  return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

export default function TelemetryPanel() {
  const { telemetry, connected } = useTelemetry()
  const [selectedDriver, setSelectedDriver] = useState<number | null>(null)

  useEffect(() => {
    if (telemetry && selectedDriver === null) {
      setSelectedDriver(telemetry.driver_number)
    }
  }, [telemetry, selectedDriver])

  if (!telemetry) {
    return (
      <div style={{ padding: 16, color: 'var(--fg-secondary)' }}>
        {connected ? 'Waiting for telemetry...' : 'Disconnected'}
      </div>
    )
  }

  return (
    <div style={{ borderTop: '1px solid var(--border)', padding: 16, overflowY: 'auto' }}>
      <h3 style={{ margin: '0 0 12px 0' }}>Telemetry</h3>
      <div style={{ fontSize: 12, color: 'var(--fg-secondary)', marginBottom: 12 }}>
        Driver {telemetry.driver_number} {telemetry.driver_name ?? ''} · {telemetry.team_name ?? ''}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>Speed</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{telemetry.speed?.toFixed(0) ?? '--'} km/h</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>RPM</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{telemetry.rpm?.toLocaleString() ?? '--'}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>Gear</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{telemetry.gear ?? '--'}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-secondary)' }}>DRS</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{telemetry.drs ? 'ON' : 'OFF'}</div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--fg-secondary)', marginBottom: 4 }}>Tyre</div>
        <div>
          {telemetry.compound ?? 'UNKNOWN'} · Age {telemetry.tyre_age ?? 0} laps · Life {telemetry.tyre_life_remaining?.toFixed(0) ?? '--'}%
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--fg-secondary)', marginBottom: 4 }}>Lap Times</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div>Current: {formatTime(telemetry.current_lap_time)}</div>
          <div>Last: {formatTime(telemetry.last_lap_time)}</div>
          <div>Best: {formatTime(telemetry.best_lap_time)}</div>
          <div>Pos: {telemetry.position ?? '--'}</div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--fg-secondary)', marginBottom: 4 }}>Sectors</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          <div>S1<br/><strong>{formatTime(telemetry.sector1_time)}</strong></div>
          <div>S2<br/><strong>{formatTime(telemetry.sector2_time)}</strong></div>
          <div>S3<br/><strong>{formatTime(telemetry.sector3_time)}</strong></div>
        </div>
      </div>

      <div style={{ marginTop: 16, fontSize: 12, color: 'var(--fg-secondary)' }}>
        Throttle {telemetry.throttle?.toFixed(0) ?? '--'}% · Brake {telemetry.brake?.toFixed(0) ?? '--'}%
      </div>
    </div>
  )
}

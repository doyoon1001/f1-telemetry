export type TyreCompound = 'SOFT' | 'MEDIUM' | 'HARD' | 'INTERMEDIATE' | 'WET' | 'UNKNOWN'

export interface DriverTelemetry {
  driver_number: number
  driver_name?: string
  team_name?: string
  team_color?: string

  x?: number
  y?: number
  lat?: number
  lon?: number

  speed?: number
  rpm?: number
  gear?: number
  throttle?: number
  brake?: number
  drs?: number

  compound?: TyreCompound
  tyre_age?: number
  tyre_life_remaining?: number

  current_lap_time?: number
  last_lap_time?: number
  best_lap_time?: number
  sector1_time?: number
  sector2_time?: number
  sector3_time?: number
  best_sector1?: number
  best_sector2?: number
  best_sector3?: number

  is_in_pit: boolean
  is_out_lap: boolean
  position?: number
  gap_to_leader?: number
  interval_to_ahead?: number

  timestamp: string
}

export interface SessionInfo {
  session_key: number
  meeting_key: number
  circuit_key: number
  session_type: string
  session_name: string
  date_start: string
  date_end?: string
  year: number
  circuit_short_name: string
  country_code: string
}

export interface TrackData {
  circuit_key: number
  circuit_short_name: string
  country_code: string
  country_name: string
  location: string
  centerline: number[][]
  corners: Array<Record<string, unknown>>
  boundaries: number[][][]
}

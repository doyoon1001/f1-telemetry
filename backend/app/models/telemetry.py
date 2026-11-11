from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class TyreCompound(str, Enum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    UNKNOWN = "UNKNOWN"


class SessionType(str, Enum):
    FP1 = "FP1"
    FP2 = "FP2"
    FP3 = "FP3"
    QUALIFYING = "QUALIFYING"
    SPRINT = "SPRINT"
    RACE = "RACE"

# 세션 타입 매핑 (FastF1 스타일 별칭)
SESSION_TYPE_ALIASES = {
    "R": "RACE",
    "Q": "QUALIFYING",
    "S": "SPRINT",
}


class DriverTelemetry(BaseModel):
    """실시간 드라이버 텔레메트리"""
    driver_number: int
    driver_name: Optional[str] = None
    team_name: Optional[str] = None
    team_color: Optional[str] = None

    # 위치
    x: Optional[float] = None
    y: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    # 주행 데이터
    speed: Optional[float] = None  # km/h
    rpm: Optional[int] = None
    gear: Optional[int] = None
    throttle: Optional[float] = None  # 0-100
    brake: Optional[float] = None  # 0-100
    drs: Optional[int] = None  # 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18

    # 타이어
    compound: Optional[TyreCompound] = None
    tyre_age: Optional[int] = None  # 랩 수
    tyre_life_remaining: Optional[float] = None  # 0-100%

    # 랩타임
    current_lap_time: Optional[float] = None  # 초
    last_lap_time: Optional[float] = None
    best_lap_time: Optional[float] = None
    sector1_time: Optional[float] = None
    sector2_time: Optional[float] = None
    sector3_time: Optional[float] = None
    best_sector1: Optional[float] = None
    best_sector2: Optional[float] = None
    best_sector3: Optional[float] = None

    # 상태
    is_in_pit: bool = False
    is_out_lap: bool = False
    position: Optional[int] = None
    gap_to_leader: Optional[float] = None  # 초
    interval_to_ahead: Optional[float] = None

    # 메타
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LapData(BaseModel):
    """랩 데이터"""
    driver_number: int
    lap_number: int
    lap_time: Optional[float] = None
    sector1_time: Optional[float] = None
    sector2_time: Optional[float] = None
    sector3_time: Optional[float] = None
    compound: Optional[TyreCompound] = None
    tyre_age: Optional[int] = None
    is_personal_best: bool = False
    is_overall_best: bool = False
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TrackData(BaseModel):
    """트랙 데이터"""
    circuit_key: int
    circuit_short_name: str
    country_code: str
    country_name: str
    location: str
    # 트랙 중심선 좌표 (x, y) 리스트
    centerline: list[list[float]] = []
    # 코너 정보
    corners: list[dict] = []
    # 바운더리
    boundaries: list[list[list[float]]] = []


class SessionInfo(BaseModel):
    """세션 정보"""
    session_key: int
    meeting_key: int
    circuit_key: int
    session_type: SessionType
    session_name: str
    date_start: datetime
    date_end: Optional[datetime] = None
    year: int
    circuit_short_name: str
    country_code: str
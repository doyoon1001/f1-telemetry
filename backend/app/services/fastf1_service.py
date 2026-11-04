import fastf1
import fastf1.plotting
from fastf1.core import Session
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
import os

from app.models.telemetry import (
    SessionInfo, TrackData, LapData, TyreCompound,
    SessionType
)
from app.core.config import get_settings


class FastF1Service:
    """FastF1을 사용한 세션 데이터 및 트랙 데이터 수집"""

    def __init__(self):
        self.settings = get_settings()
        self._setup_cache()
        self._session: Optional[Session] = None

    def _setup_cache(self):
        """FastF1 캐시 설정"""
        cache_dir = self.settings.fastf1_cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)

    def get_session(self, year: int, gp: str, session_type: str) -> SessionInfo:
        """세션 로드 및 정보 반환"""
        session = fastf1.get_session(year, gp, session_type)
        session.load()

        self._session = session

        return SessionInfo(
            session_key=session.session_key,
            meeting_key=session.meeting_key,
            circuit_key=session.circuit_key,
            session_type=SessionType(session.session_type),
            session_name=session.name,
            date_start=session.date_start,
            date_end=session.date_end,
            year=session.event.year,
            circuit_short_name=session.event.CircuitShortName,
            country_code=session.event.CountryCode
        )

    def get_track_data(self) -> TrackData:
        """트랙 데이터 추출 (중심선, 코너, 바운더리)"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음. get_session()을 먼저 호출하세요.")

        circuit_info = self._session.get_circuit_info()

        # 중심선 좌표
        centerline = []
        if hasattr(circuit_info, 'corners') and len(circuit_info.corners) > 0:
            # FastF1에서 제공하는 회전 정보로 대략적인 트랙 형태 구성
            pass

        # 더 정확한 트랙 데이터는 OpenF1 REST API에서 가져오는 것이 좋음
        # 여기서는 기본 구조만 반환
        return TrackData(
            circuit_key=self._session.circuit_key,
            circuit_short_name=self._session.event.CircuitShortName,
            country_code=self._session.event.CountryCode,
            country_name=self._session.event.CountryName,
            location=self._session.event.Location,
            centerline=[],
            corners=[],
            boundaries=[]
        )

    def get_laps_data(self, driver: Optional[str] = None) -> List[LapData]:
        """랩 데이터 추출"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음.")

        laps = self._session.laps

        if driver:
            laps = laps.pick_driver(driver)

        lap_list = []
        for _, lap in laps.iterlaps():
            if pd.isna(lap.LapTime):
                continue

            compound = lap.Compound
            if isinstance(compound, str):
                try:
                    compound = TyreCompound(compound.upper())
                except ValueError:
                    compound = TyreCompound.UNKNOWN

            lap_data = LapData(
                driver_number=lap.DriverNumber,
                lap_number=int(lap.LapNumber),
                lap_time=lap.LapTime.total_seconds() if not pd.isna(lap.LapTime) else None,
                sector1_time=lap.Sector1Time.total_seconds() if not pd.isna(lap.Sector1Time) else None,
                sector2_time=lap.Sector2Time.total_seconds() if not pd.isna(lap.Sector2Time) else None,
                sector3_time=lap.Sector3Time.total_seconds() if not pd.isna(lap.Sector3Time) else None,
                compound=compound,
                tyre_age=int(lap.TyreLife) if not pd.isna(lap.TyreLife) else None,
                is_personal_best=lap.IsPersonalBest,
                is_overall_best=lap.IsOverallBest,
                started_at=lap.LapStartTime if not pd.isna(lap.LapStartTime) else None,
            )
            lap_list.append(lap_data)

        return lap_list

    def get_driver_summary(self, driver: str) -> Dict[str, Any]:
        """드라이버별 요약 통계"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음.")

        laps = self._session.laps.pick_driver(driver)

        if laps.empty:
            return {}

        valid_laps = laps.dropna(subset=['LapTime'])
        if valid_laps.empty:
            return {}

        best_lap = valid_laps.pick_fastest()

        return {
            'driver': driver,
            'total_laps': len(valid_laps),
            'best_lap_time': best_lap.LapTime.total_seconds() if not pd.isna(best_lap.LapTime) else None,
            'best_sector1': best_lap.Sector1Time.total_seconds() if not pd.isna(best_lap.Sector1Time) else None,
            'best_sector2': best_lap.Sector2Time.total_seconds() if not pd.isna(best_lap.Sector2Time) else None,
            'best_sector3': best_lap.Sector3Time.total_seconds() if not pd.isna(best_lap.Sector3Time) else None,
            'compound_used': valid_laps['Compound'].dropna().unique().tolist(),
            'avg_lap_time': valid_laps['LapTime'].dt.total_seconds().mean(),
            'stint_count': valid_laps['Stint'].nunique() if 'Stint' in valid_laps.columns else 0
        }

    def get_all_drivers_summary(self) -> List[Dict[str, Any]]:
        """모든 드라이버 요약"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음.")

        drivers = self._session.drivers
        summaries = []

        for driver in drivers:
            try:
                summary = self.get_driver_summary(driver)
                if summary:
                    summary['driver_code'] = driver
                    summaries.append(summary)
            except Exception:
                continue

        return summaries

    def get_track_layout_for_map(self) -> Dict[str, Any]:
        """프론트엔드 맵 렌더링용 트랙 레이아웃"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음.")

        circuit_info = self._session.get_circuit_info()

        # 코너 정보 추출
        corners = []
        if hasattr(circuit_info, 'corners'):
            for _, corner in circuit_info.corners.iterrows():
                corners.append({
                    'number': int(corner.Number) if not pd.isna(corner.Number) else None,
                    'letter': corner.Letter if not pd.isna(corner.Letter) else None,
                    'x': float(corner.X) if not pd.isna(corner.X) else None,
                    'y': float(corner.Y) if not pd.isna(corner.Y) else None,
                    'angle': float(corner.Angle) if not pd.isna(corner.Angle) else None
                })

        # 회전 경로 (트랙 중심선 근사)
        # FastF1에서 정확한 중심선을 얻기 어려우므로 코너 점들을 연결
        track_path = []
        if corners:
            for c in corners:
                if c['x'] is not None and c['y'] is not None:
                    track_path.append([c['x'], c['y']])

        return {
            'circuit_name': self._session.event.CircuitShortName,
            'corners': corners,
            'track_path': track_path,
            'bounds': self._calculate_bounds(corners)
        }

    def _calculate_bounds(self, corners: List[Dict]) -> Dict[str, float]:
        """트랙 바운더리 계산"""
        xs = [c['x'] for c in corners if c['x'] is not None]
        ys = [c['y'] for c in corners if c['y'] is not None]

        if not xs or not ys:
            return {'min_x': -1000, 'max_x': 1000, 'min_y': -1000, 'max_y': 1000}

        padding = 500
        return {
            'min_x': min(xs) - padding,
            'max_x': max(xs) + padding,
            'min_y': min(ys) - padding,
            'max_y': max(ys) + padding
        }
import fastf1
import fastf1.plotting
from fastf1.core import Session
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
import os
import httpx

from app.models.telemetry import (
    SessionInfo, TrackData, LapData, TyreCompound,
    SessionType, SESSION_TYPE_ALIASES
)
from app.core.config import get_settings


# GP별 circuit_key 매핑 (OpenF1 기준 - MultiViewer API용)
CIRCUIT_KEY_MAP = {
    'bahrain': 63, 'saudi_arabia': 149, 'australia': 10, 'japan': 46, 'china': 49,
    'miami': 151, 'emilia_romagna': 6, 'monaco': 22, 'canada': 23, 'spain': 15,
    'austria': 19, 'great_britain': 2, 'hungary': 4, 'belgium': 7, 'netherlands': 55,
    'italy': 39, 'azerbaijan': 144, 'singapore': 61, 'united_states': 9, 'mexico': 65,
    'brazil': 14, 'las_vegas': 152, 'qatar': 150, 'abu_dhabi': 70,
    'monza': 39,  # alias
}

# FastF1 circuit_key 매핑 (별도)
FASTF1_CIRCUIT_KEY_MAP = {
    'bahrain': 1, 'saudi_arabia': 2, 'australia': 3, 'japan': 4, 'china': 5,
    'miami': 6, 'emilia_romagna': 7, 'monaco': 8, 'canada': 9, 'spain': 10,
    'austria': 11, 'great_britain': 12, 'hungary': 13, 'belgium': 14, 'netherlands': 15,
    'italy': 16, 'azerbaijan': 17, 'singapore': 18, 'united_states': 19, 'mexico': 20,
    'brazil': 21, 'las_vegas': 22, 'qatar': 23, 'abu_dhabi': 24,
    'monza': 16,
}


# 모나코 서킷 폴백 데이터 (API 실패 시)
MONACO_FALLBACK_CORNERS = [
    {'number': 1, 'letter': None, 'x': 0.0, 'y': 0.0, 'angle': 90.0},
    {'number': 2, 'letter': None, 'x': 50.0, 'y': -200.0, 'angle': -45.0},
    {'number': 3, 'letter': None, 'x': 300.0, 'y': -150.0, 'angle': -90.0},
    {'number': 4, 'letter': None, 'x': 400.0, 'y': 100.0, 'angle': 180.0},
    {'number': 5, 'letter': None, 'x': 200.0, 'y': 300.0, 'angle': 90.0},
    {'number': 6, 'letter': None, 'x': -100.0, 'y': 400.0, 'angle': -90.0},
    {'number': 7, 'letter': None, 'x': -300.0, 'y': 200.0, 'angle': 180.0},
    {'number': 8, 'letter': None, 'x': -400.0, 'y': -100.0, 'angle': -90.0},
    {'number': 9, 'letter': None, 'x': -200.0, 'y': -300.0, 'angle': 90.0},
    {'number': 10, 'letter': None, 'x': 0.0, 'y': -100.0, 'angle': 0.0},
    {'number': 11, 'letter': None, 'x': 150.0, 'y': -50.0, 'angle': -45.0},
    {'number': 12, 'letter': None, 'x': 200.0, 'y': 100.0, 'angle': 90.0},
    {'number': 13, 'letter': None, 'x': 100.0, 'y': 200.0, 'angle': 180.0},
    {'number': 14, 'letter': None, 'x': -50.0, 'y': 150.0, 'angle': -90.0},
    {'number': 15, 'letter': None, 'x': -150.0, 'y': 50.0, 'angle': 0.0},
    {'number': 16, 'letter': None, 'x': -100.0, 'y': -50.0, 'angle': 90.0},
    {'number': 17, 'letter': None, 'x': 0.0, 'y': -100.0, 'angle': 180.0},
    {'number': 18, 'letter': None, 'x': 50.0, 'y': 0.0, 'angle': -90.0},
    {'number': 19, 'letter': None, 'x': 100.0, 'y': -100.0, 'angle': 0.0},
]

FALLBACK_TRACKS = {
    'monaco': {
        'name': 'Monaco',
        'circuit_short_name': 'Monaco',
        'country_code': 'MCO',
        'country_name': 'Monaco',
        'location': 'Monaco',
        'corners': MONACO_FALLBACK_CORNERS,
    },
    'bahrain': {
        'name': 'Bahrain',
        'circuit_short_name': 'Bahrain',
        'country_code': 'BHR',
        'country_name': 'Bahrain',
        'location': 'Sakhir',
        'corners': [
            {'number': i, 'letter': None, 'x': 500*np.cos(2*np.pi*i/15), 'y': 500*np.sin(2*np.pi*i/15), 'angle': 45.0}
            for i in range(15)
        ],
    },
    'silverstone': {
        'name': 'Great Britain',
        'circuit_short_name': 'Silverstone',
        'country_code': 'GBR',
        'country_name': 'United Kingdom',
        'location': 'Silverstone',
        'corners': [
            {'number': i, 'letter': None, 'x': 600*np.cos(2*np.pi*i/18), 'y': 600*np.sin(2*np.pi*i/18), 'angle': 45.0}
            for i in range(18)
        ],
    },
    'italy': {
        'name': 'Monza',
        'circuit_short_name': 'Monza',
        'country_code': 'ITA',
        'country_name': 'Italy',
        'location': 'Monza',
        'corners': [
            {'number': 1, 'letter': None, 'x': 0.0, 'y': 0.0, 'angle': -90.0},
            {'number': 2, 'letter': None, 'x': 50.0, 'y': 50.0, 'angle': 90.0},
            {'number': 3, 'letter': None, 'x': 300.0, 'y': -100.0, 'angle': -120.0},
            {'number': 4, 'letter': None, 'x': 500.0, 'y': -200.0, 'angle': 110.0},
            {'number': 5, 'letter': None, 'x': 550.0, 'y': -150.0, 'angle': -90.0},
            {'number': 6, 'letter': None, 'x': 600.0, 'y': 100.0, 'angle': -100.0},
            {'number': 7, 'letter': None, 'x': 650.0, 'y': 250.0, 'angle': -80.0},
            {'number': 8, 'letter': None, 'x': 500.0, 'y': 400.0, 'angle': 120.0},
            {'number': 9, 'letter': None, 'x': 450.0, 'y': 350.0, 'angle': -90.0},
            {'number': 10, 'letter': None, 'x': 400.0, 'y': 400.0, 'angle': 100.0},
            {'number': 11, 'letter': None, 'x': 200.0, 'y': 300.0, 'angle': -150.0},
        ],
    },
    'monza': {
        'name': 'Monza',
        'circuit_short_name': 'Monza',
        'country_code': 'ITA',
        'country_name': 'Italy',
        'location': 'Monza',
        'corners': [
            {'number': 1, 'letter': None, 'x': 0.0, 'y': 0.0, 'angle': -90.0},
            {'number': 2, 'letter': None, 'x': 50.0, 'y': 50.0, 'angle': 90.0},
            {'number': 3, 'letter': None, 'x': 300.0, 'y': -100.0, 'angle': -120.0},
            {'number': 4, 'letter': None, 'x': 500.0, 'y': -200.0, 'angle': 110.0},
            {'number': 5, 'letter': None, 'x': 550.0, 'y': -150.0, 'angle': -90.0},
            {'number': 6, 'letter': None, 'x': 600.0, 'y': 100.0, 'angle': -100.0},
            {'number': 7, 'letter': None, 'x': 650.0, 'y': 250.0, 'angle': -80.0},
            {'number': 8, 'letter': None, 'x': 500.0, 'y': 400.0, 'angle': 120.0},
            {'number': 9, 'letter': None, 'x': 450.0, 'y': 350.0, 'angle': -90.0},
            {'number': 10, 'letter': None, 'x': 400.0, 'y': 400.0, 'angle': 100.0},
            {'number': 11, 'letter': None, 'x': 200.0, 'y': 300.0, 'angle': -150.0},
        ],
    },
}


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
        # 세션 타입 별칭 매핑 (R -> RACE 등)
        normalized_session_type = SESSION_TYPE_ALIASES.get(session_type.upper(), session_type)

        session = fastf1.get_session(year, gp, normalized_session_type)
        session.load()

        self._session = session

        # FastF1 3.9+ API에서 사용 가능한 필드 매핑
        event = session.event
        circuit_name = getattr(event, 'Location', getattr(event, 'Country', gp))
        country_code = getattr(event, 'Country', '')
        
        # circuit_key 매핑
        gp_lower = gp.lower().replace(' ', '_')
        circuit_key = CIRCUIT_KEY_MAP.get(gp_lower, 0)

        return SessionInfo(
            session_key=id(session),  # 대체값
            meeting_key=0,  # 대체값
            circuit_key=circuit_key,  # 실제 circuit_key 사용
            session_type=SessionType(normalized_session_type),
            session_name=session.name,
            date_start=session.date,
            date_end=None,
            year=int(event.get('year', year)),
            circuit_short_name=circuit_name,
            country_code=country_code
        )

    def _get_fallback_track_data(self, gp: str) -> Dict[str, Any]:
        """폴백 트랙 데이터 반환 (API 실패 시)"""
        gp_lower = gp.lower().replace(' ', '_')
        return FALLBACK_TRACKS.get(gp_lower, FALLBACK_TRACKS['monaco'])

    def _get_track_from_multiviewer(self, circuit_key: int, year: int) -> Optional[Dict[str, Any]]:
        """MultiViewer API에서 실제 트랙 데이터 가져오기"""
        try:
            url = f"https://api.multiviewer.app/api/v1/circuits/{circuit_key}/{year}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = httpx.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                # 중심선 좌표 (x, y 리스트)
                centerline = list(zip(data.get('x', []), data.get('y', [])))
                # 코너 정보
                corners = []
                for c in data.get('corners', []):
                    pos = c.get('trackPosition', {})
                    corners.append({
                        'number': c.get('number'),
                        'letter': None,
                        'x': float(pos.get('x', 0)),
                        'y': float(pos.get('y', 0)),
                        'angle': float(c.get('angle', 0))
                    })
                return {
                    'centerline': [[float(x), float(y)] for x, y in centerline],
                    'corners': corners,
                    'rotation': data.get('rotation', 0)
                }
        except Exception as e:
            print(f"MultiViewer API error: {e}")
        return None

    def get_track_data(self) -> TrackData:
        """트랙 데이터 추출 (중심선, 코너, 바운더리) - MultiViewer API 우선 사용"""
        if not self._session:
            raise ValueError("세션이 로드되지 않음. get_session()을 먼저 호출하세요.")

        event = self._session.event
        gp_name = getattr(event, 'Location', getattr(event, 'Country', 'Unknown'))
        year = int(getattr(event, 'year', 2024))

        gp_lower = gp_name.lower().replace(' ', '_')

        # MultiViewer용 circuit_key (OpenF1 기준)
        mv_circuit_key = CIRCUIT_KEY_MAP.get(gp_lower, 0)
        # FastF1용 circuit_key
        ff_circuit_key = FASTF1_CIRCUIT_KEY_MAP.get(gp_lower, 0)

        circuit_name = getattr(event, 'Location', getattr(event, 'Country', gp_name))
        country_code = getattr(event, 'Country', '')

        # 1순위: MultiViewer API로 실제 트랙 데이터 가져오기
        track_data = None
        if mv_circuit_key:
            track_data = self._get_track_from_multiviewer(mv_circuit_key, year)

        # 2순위: FastF1 circuit_info
        if not track_data:
            try:
                circuit_info = self._session.get_circuit_info()
                if hasattr(circuit_info, 'corners') and len(circuit_info.corners) > 0:
                    corners = []
                    track_path = []
                    for _, corner in circuit_info.corners.iterrows():
                        c = {
                            'number': int(corner.Number) if not pd.isna(corner.Number) else None,
                            'letter': corner.Letter if not pd.isna(corner.Letter) else None,
                            'x': float(corner.X) if not pd.isna(corner.X) else None,
                            'y': float(corner.Y) if not pd.isna(corner.Y) else None,
                            'angle': float(corner.Angle) if not pd.isna(corner.Angle) else None
                        }
                        corners.append(c)
                        if c['x'] is not None and c['y'] is not None:
                            track_path.append([c['x'], c['y']])
                    if corners:
                        track_data = {
                            'centerline': track_path,
                            'corners': corners,
                            'rotation': 0
                        }
            except Exception:
                pass

        # 3순위: 폴백 데이터
        if not track_data:
            fallback = self._get_fallback_track_data(gp_name)
            corners = fallback['corners']
            track_path = [[c['x'], c['y']] for c in corners if c['x'] is not None and c['y'] is not None]
            track_data = {
                'centerline': track_path,
                'corners': corners,
                'rotation': 0
            }

        # TrackData 객체 생성
        final_circuit_key = mv_circuit_key if mv_circuit_key else ff_circuit_key

        if track_data and track_data.get('centerline'):
            # 회전 적용 (MultiViewer rotation 값 사용)
            rotation = track_data.get('rotation', 0)
            centerline = track_data['centerline']
            corners = track_data['corners']

            # rotation이 0이 아니면 좌표 회전 (라디안)
            if rotation:
                import math
                rad = math.radians(rotation)
                cos_r, sin_r = math.cos(rad), math.sin(rad)
                centerline = [[x * cos_r - y * sin_r, x * sin_r + y * cos_r] for x, y in centerline]
                for c in corners:
                    if c['x'] is not None and c['y'] is not None:
                        x, y = c['x'], c['y']
                        c['x'] = x * cos_r - y * sin_r
                        c['y'] = x * sin_r + y * cos_r

            return TrackData(
                circuit_key=final_circuit_key,
                circuit_short_name=circuit_name,
                country_code=country_code,
                country_name=country_code,
                location=circuit_name,
                centerline=centerline,
                corners=corners,
                boundaries=[]
            )

        # 최후 폴백
        fallback = self._get_fallback_track_data(gp_name)
        corners = fallback['corners']
        track_path = [[c['x'], c['y']] for c in corners if c['x'] is not None and c['y'] is not None]

        return TrackData(
            circuit_key=final_circuit_key,
            circuit_short_name=circuit_name,
            country_code=country_code,
            country_name=fallback.get('country_name', country_code),
            location=fallback.get('location', circuit_name),
            centerline=track_path,
            corners=corners,
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

        event = self._session.event
        gp_name = getattr(event, 'Location', getattr(event, 'Country', 'Unknown'))
        fallback = self._get_fallback_track_data(gp_name)

        # FastF1 회로 정보 시도
        try:
            circuit_info = self._session.get_circuit_info()
            has_circuit_info = True
        except Exception:
            has_circuit_info = False

        circuit_name = getattr(event, 'Location', getattr(event, 'Country', gp_name))

        # 코너 정보 추출
        corners = []
        if has_circuit_info and hasattr(circuit_info, 'corners'):
            for _, corner in circuit_info.corners.iterrows():
                corners.append({
                    'number': int(corner.Number) if not pd.isna(corner.Number) else None,
                    'letter': corner.Letter if not pd.isna(corner.Letter) else None,
                    'x': float(corner.X) if not pd.isna(corner.X) else None,
                    'y': float(corner.Y) if not pd.isna(corner.Y) else None,
                    'angle': float(corner.Angle) if not pd.isna(corner.Angle) else None
                })

        # FastF1 데이터가 없으면 폴백 사용
        if not corners:
            corners = fallback['corners']

        # 회전 경로 (트랙 중심선 근사)
        track_path = []
        if corners:
            for c in corners:
                if c['x'] is not None and c['y'] is not None:
                    track_path.append([c['x'], c['y']])

        return {
            'circuit_name': circuit_name,
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
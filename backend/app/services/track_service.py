import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models.telemetry import TrackData, SessionInfo, SessionType
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TrackService:
    """트랙 데이터 변환 및 프론트엔드용 포맷팅"""

    def __init__(self):
        self.settings = get_settings()
        self._track_cache: Dict[int, TrackData] = {}

    def get_track_for_map(self, circuit_key: int) -> Optional[TrackData]:
        """캐시된 트랙 데이터 반환"""
        return self._track_cache.get(circuit_key)

    def cache_track(self, track_data: TrackData):
        """트랙 데이터 캐싱"""
        self._track_cache[track_data.circuit_key] = track_data

    def format_for_leaflet(self, track_data: TrackData) -> Dict[str, Any]:
        """Leaflet 지도 렌더링용 포맷"""
        return {
            'circuit_key': track_data.circuit_key,
            'circuit_name': track_data.circuit_short_name,
            'centerline': track_data.centerline,
            'corners': track_data.corners,
            'boundaries': track_data.boundaries,
        }

    def format_for_canvas(self, track_data: TrackData, canvas_size: tuple = (800, 600)) -> Dict[str, Any]:
        """Canvas 렌더링용 좌표 변환 (정규화)"""
        bounds = self._calculate_bounds(track_data)
        if not bounds:
            return {}

        width, height = canvas_size
        padding = 40

        def transform(x: float, y: float) -> tuple:
            """트랙 좌표 → 캔버스 좌표"""
            norm_x = (x - bounds['min_x']) / (bounds['max_x'] - bounds['min_x'])
            norm_y = (y - bounds['min_y']) / (bounds['max_y'] - bounds['min_y'])
            canvas_x = padding + norm_x * (width - 2 * padding)
            canvas_y = padding + (1 - norm_y) * (height - 2 * padding)  # Y축 뒤집기
            return (canvas_x, canvas_y)

        centerline_canvas = [
            transform(x, y) for x, y in track_data.centerline
        ] if track_data.centerline else []

        corners_canvas = []
        for corner in track_data.corners:
            if corner.get('x') is not None and corner.get('y') is not None:
                cx, cy = transform(corner['x'], corner['y'])
                corners_canvas.append({
                    **corner,
                    'canvas_x': cx,
                    'canvas_y': cy
                })

        boundaries_canvas = []
        for boundary in track_data.boundaries:
            boundaries_canvas.append([
                transform(x, y) for x, y in boundary
            ])

        return {
            'width': width,
            'height': height,
            'centerline': centerline_canvas,
            'corners': corners_canvas,
            'boundaries': boundaries_canvas,
            'bounds': bounds
        }

    def _calculate_bounds(self, track_data: TrackData) -> Optional[Dict[str, float]]:
        """트랙 바운더리 계산"""
        xs, ys = [], []

        for x, y in track_data.centerline:
            xs.append(x)
            ys.append(y)

        for corner in track_data.corners:
            if corner.get('x') is not None:
                xs.append(corner['x'])
            if corner.get('y') is not None:
                ys.append(corner['y'])

        for boundary in track_data.boundaries:
            for x, y in boundary:
                xs.append(x)
                ys.append(y)

        if not xs or not ys:
            return None

        padding = 500
        return {
            'min_x': min(xs) - padding,
            'max_x': max(xs) + padding,
            'min_y': min(ys) - padding,
            'max_y': max(ys) + padding
        }

    def get_car_position_on_track(self, car_x: float, car_y: float, track_data: TrackData) -> Optional[Dict[str, Any]]:
        """차량 위치를 트랙 상의 진행도(0-1)로 변환"""
        if not track_data.centerline or len(track_data.centerline) < 2:
            return None

        # 가장 가까운 중심선 점 찾기
        min_dist = float('inf')
        closest_idx = 0

        for i, (cx, cy) in enumerate(track_data.centerline):
            dist = (car_x - cx) ** 2 + (car_y - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        # 진행도 계산 (0.0 ~ 1.0)
        progress = closest_idx / (len(track_data.centerline) - 1) if len(track_data.centerline) > 1 else 0

        # 해당 지점의 방향 벡터 계산 (헤딩용)
        heading = 0
        if closest_idx < len(track_data.centerline) - 1:
            x1, y1 = track_data.centerline[closest_idx]
            x2, y2 = track_data.centerline[closest_idx + 1]
            import math
            heading = math.atan2(y2 - y1, x2 - x1)

        return {
            'progress': progress,
            'closest_point_index': closest_idx,
            'distance_to_line': min_dist ** 0.5,
            'heading': heading
        }
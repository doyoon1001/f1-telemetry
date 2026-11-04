import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
import websockets
from websockets.client import WebSocketClientProtocol
from datetime import datetime

from app.models.telemetry import DriverTelemetry, TyreCompound
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenF1Service:
    """OpenF1 WebSocket 실시간 텔레메트리 수집"""

    def __init__(self):
        self.settings = get_settings()
        self.ws: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.callbacks: list[Callable[[DriverTelemetry], Awaitable[None]]] = []
        self.driver_info: Dict[int, Dict[str, Any]] = {}
        self._task: Optional[asyncio.Task] = None

    def register_callback(self, callback: Callable[[DriverTelemetry], Awaitable[None]]):
        """텔레메트리 수신 시 호출될 콜백 등록"""
        self.callbacks.append(callback)

    async def connect(self):
        """WebSocket 연결"""
        try:
            self.ws = await websockets.connect(self.settings.openf1_ws_url)
            logger.info(f"Connected to OpenF1 WebSocket: {self.settings.openf1_ws_url}")
            self.running = True
            self._task = asyncio.create_task(self._listen())
        except Exception as e:
            logger.error(f"Failed to connect to OpenF1: {e}")
            raise

    async def disconnect(self):
        """연결 종료"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
        logger.info("Disconnected from OpenF1")

    async def _listen(self):
        """메시지 수신 루프"""
        try:
            async for message in self.ws:
                if not self.running:
                    break
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("OpenF1 WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")

    async def _process_message(self, message: str):
        """메시지 파싱 및 콜백 호출"""
        try:
            data = json.loads(message)

            # OpenF1 메시지 타입 확인
            # 실제 메시지 구조에 따라 파싱 로직 조정 필요
            telemetry = self._parse_telemetry(data)
            if telemetry:
                await self._notify_callbacks(telemetry)

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _parse_telemetry(self, data: Dict[str, Any]) -> Optional[DriverTelemetry]:
        """OpenF1 메시지 파싱 - 실제 API 응답 구조에 맞게 조정 필요"""
        try:
            # OpenF1 실시간 스트림 메시지 구조 예시:
            # {
            #   "driver_number": 1,
            #   "x": 123.4, "y": 567.8,
            #   "speed": 280, "gear": 7, "drs": 1,
            #   "compound": "SOFT", "tyre_age": 5,
            #   "lap_time": 90.5, "sector1": 25.2, ...
            # }

            # OpenF1 실제 응답 구조에 맞게 조정 필요
            # 현재는 예시 구현

            driver_number = data.get('driver_number')
            if driver_number is None:
                return None

            # 드라이버 정보 병합
            driver_info = self.driver_info.get(driver_number, {})

            # 타이어 컴파운드 파싱
            compound_str = data.get('compound', 'UNKNOWN').upper()
            try:
                compound = TyreCompound(compound_str)
            except ValueError:
                compound = TyreCompound.UNKNOWN

            return DriverTelemetry(
                driver_number=driver_number,
                driver_name=driver_info.get('name'),
                team_name=driver_info.get('team'),
                team_color=driver_info.get('color'),
                x=data.get('x'),
                y=data.get('y'),
                speed=data.get('speed'),
                rpm=data.get('rpm'),
                gear=data.get('gear'),
                throttle=data.get('throttle'),
                brake=data.get('brake'),
                drs=data.get('drs'),
                compound=compound,
                tyre_age=data.get('tyre_age'),
                current_lap_time=data.get('lap_time'),
                last_lap_time=data.get('last_lap_time'),
                best_lap_time=data.get('best_lap_time'),
                sector1_time=data.get('sector1'),
                sector2_time=data.get('sector2'),
                sector3_time=data.get('sector3'),
                best_sector1=data.get('best_sector1'),
                best_sector2=data.get('best_sector2'),
                best_sector3=data.get('best_sector3'),
                is_in_pit=data.get('in_pit', False),
                position=data.get('position'),
                gap_to_leader=data.get('gap_to_leader'),
            )

        except Exception as e:
            logger.error(f"Failed to parse telemetry: {e}")
            return None

    async def _notify_callbacks(self, telemetry: DriverTelemetry):
        """등록된 모든 콜백 호출"""
        for callback in self.callbacks:
            try:
                await callback(telemetry)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def update_driver_info(self, driver_number: int, info: Dict[str, Any]):
        """드라이버 정적 정보 업데이트 (이름, 팀, 색상 등)"""
        self.driver_info[driver_number] = info

    async def fetch_driver_info_rest(self):
        """REST API로 드라이버 정보 가져오기"""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                # 드라이버 목록
                resp = await client.get(f"{self.settings.openf1_rest_url}/drivers")
                if resp.status_code == 200:
                    drivers = resp.json()
                    for d in drivers:
                        self.update_driver_info(d['driver_number'], {
                            'name': d.get('full_name') or d.get('name'),
                            'team': d.get('team_name'),
                            'color': d.get('team_colour')
                        })
        except Exception as e:
            logger.error(f"Failed to fetch driver info: {e}")


# 싱글톤 인스턴스
_openf1_service: Optional[OpenF1Service] = None


async def get_openf1_service() -> OpenF1Service:
    global _openf1_service
    if _openf1_service is None:
        _openf1_service = OpenF1Service()
    return _openf1_service
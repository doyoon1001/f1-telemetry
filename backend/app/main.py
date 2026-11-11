from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import asyncio
import logging
import random
import math
from datetime import datetime

from app.core.config import get_settings
from app.services.fastf1_service import FastF1Service
from app.services.openf1_service import OpenF1Service, get_openf1_service
from app.services.track_service import TrackService
from app.models.telemetry import (
    DriverTelemetry, SessionInfo, TrackData, LapData,
    TyreCompound, SessionType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# 서비스 인스턴스
fastf1_service = FastF1Service()
openf1_service: OpenF1Service = None  # type: ignore
track_service = TrackService()

# WebSocket 연결 관리
active_connections: List[WebSocket] = []

# 모의 데이터용 드라이버 정보 (2024 시즌)
MOCK_DRIVERS = [
    {"number": 1, "name": "Max Verstappen", "team": "Red Bull Racing", "color": "#1E41FF"},
    {"number": 11, "name": "Sergio Perez", "team": "Red Bull Racing", "color": "#1E41FF"},
    {"number": 16, "name": "Charles Leclerc", "team": "Ferrari", "color": "#E8002D"},
    {"number": 55, "name": "Carlos Sainz", "team": "Ferrari", "color": "#E8002D"},
    {"number": 44, "name": "Lewis Hamilton", "team": "Mercedes", "color": "#27F4D2"},
    {"number": 63, "name": "George Russell", "team": "Mercedes", "color": "#27F4D2"},
    {"number": 4, "name": "Lando Norris", "team": "McLaren", "color": "#FF8000"},
    {"number": 81, "name": "Oscar Piastri", "team": "McLaren", "color": "#FF8000"},
    {"number": 14, "name": "Fernando Alonso", "team": "Aston Martin", "color": "#229971"},
    {"number": 18, "name": "Lance Stroll", "team": "Aston Martin", "color": "#229971"},
]

# 모의 데이터 생성기 상태
mock_telemetry_task: asyncio.Task = None
mock_running = False


def generate_mock_telemetry() -> DriverTelemetry:
    """개발/데모용 모의 텔레메트리 생성"""
    driver = random.choice(MOCK_DRIVERS)
    
    # 트랙 위치를 원형 경로로 시뮬레이션 (모나코 기준)
    track_center = (0, 0)
    track_radius = 300
    angle = random.uniform(0, 2 * math.pi)
    
    # 속도: 80-340 km/h
    speed = random.uniform(80, 340)
    # RPM: 10000-13000
    rpm = random.randint(10000, 13000)
    # 기어: 1-8
    gear = random.randint(1, 8)
    # DRS: 직선에서만 (확률 20%)
    drs = 1 if random.random() < 0.2 else 0
    
    compounds = [TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD, TyreCompound.INTERMEDIATE, TyreCompound.WET]
    
    return DriverTelemetry(
        driver_number=driver["number"],
        driver_name=driver["name"],
        team_name=driver["team"],
        team_color=driver["color"],
        x=track_center[0] + track_radius * math.cos(angle),
        y=track_center[1] + track_radius * math.sin(angle),
        speed=speed,
        rpm=rpm,
        gear=gear,
        throttle=random.uniform(0, 100),
        brake=random.uniform(0, 100) if speed > 200 else 0,
        drs=drs,
        compound=random.choice(compounds),
        tyre_age=random.randint(1, 30),
        tyre_life_remaining=random.uniform(10, 100),
        current_lap_time=random.uniform(70, 100),
        last_lap_time=random.uniform(70, 95),
        best_lap_time=random.uniform(68, 75),
        sector1_time=random.uniform(20, 30),
        sector2_time=random.uniform(25, 35),
        sector3_time=random.uniform(20, 30),
        best_sector1=random.uniform(19, 25),
        best_sector2=random.uniform(23, 30),
        best_sector3=random.uniform(19, 25),
        is_in_pit=random.random() < 0.02,
        position=random.randint(1, 20),
        gap_to_leader=random.uniform(0, 60) if driver["number"] != 1 else 0,
    )


async def mock_telemetry_broadcaster():
    """주기적으로 모의 텔레메트리 브로드캐스트"""
    global mock_running
    mock_running = True
    logger.info("Mock telemetry broadcaster started")
    
    try:
        while mock_running:
            if active_connections:
                # 각 드라이버마다 텔레메트리 전송
                for driver in MOCK_DRIVERS:
                    if not mock_running:
                        break
                    
                    # 드라이버별로 약간 다른 데이터 생성
                    telemetry = generate_mock_telemetry()
                    # 선택된 드라이버 번호 강제 적용
                    telemetry.driver_number = driver["number"]
                    telemetry.driver_name = driver["name"]
                    telemetry.team_name = driver["team"]
                    telemetry.team_color = driver["color"]
                    
                    await broadcast_telemetry(telemetry)
                    await asyncio.sleep(0.1)  # 드라이버 간 간격
                
                await asyncio.sleep(0.5)  # 전체 사이클 간격
            else:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Mock telemetry broadcaster cancelled")
    except Exception as e:
        logger.error(f"Mock telemetry error: {e}")
    finally:
        mock_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    global openf1_service, mock_telemetry_task
    logger.info("Starting F1 Telemetry Backend...")

    # OpenF1 서비스 초기화
    openf1_service = await get_openf1_service()
    openf1_service.register_callback(broadcast_telemetry)

    openf1_connected = False
    try:
        await openf1_service.connect()
        await openf1_service.fetch_driver_info_rest()
        openf1_connected = True
        logger.info("OpenF1 connected successfully")
    except Exception as e:
        logger.warning(f"OpenF1 connection failed: {e}")

    # OpenF1 연결 실패 시 모의 데이터 브로드캐스터 시작
    if not openf1_connected:
        logger.info("Starting mock telemetry broadcaster for development...")
        mock_telemetry_task = asyncio.create_task(mock_telemetry_broadcaster())

    yield

    # 종료 시
    logger.info("Shutting down...")
    if mock_telemetry_task:
        mock_telemetry_task.cancel()
        try:
            await mock_telemetry_task
        except asyncio.CancelledError:
            pass
    if openf1_service:
        await openf1_service.disconnect()


app = FastAPI(
    title="F1 Telemetry API",
    description="Real-time F1 telemetry dashboard backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket 연결 관리
async def broadcast_telemetry(telemetry: DriverTelemetry):
    """모든 연결된 클라이언트에게 텔레메트리 브로드캐스트"""
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json({
                "type": "telemetry",
                "data": telemetry.model_dump(mode='json')
            })
        except Exception:
            disconnected.append(ws)

    # 끊어진 연결 정리
    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket connected. Total: {len(active_connections)}")

    try:
        # 현재 드라이버 정보 전송
        # TODO: 현재 세션의 드라이버 리스트 전송
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to F1 Telemetry stream"
        })

        # 클라이언트 메시지 대기 (핑퐁 등)
        while True:
            data = await websocket.receive_text()
            # 클라이언트에서 오는 메시지 처리 (필터링 요청 등)
            pass

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


# REST API 라우트
@app.get("/")
async def root():
    return {
        "service": "F1 Telemetry API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "websocket_connections": len(active_connections),
        "openf1_connected": openf1_service.running if openf1_service else False
    }


# 세션 관련 API
@app.post("/api/session/load")
async def load_session(year: int, gp: str, session_type: str):
    """세션 로드 (FastF1)"""
    try:
        session_info = fastf1_service.get_session(year, gp, session_type)

        # 트랙 데이터 캐싱
        track_data = fastf1_service.get_track_data()
        track_service.cache_track(track_data)

        return {
            "success": True,
            "session": session_info.model_dump(mode='json'),
            "track": track_data.model_dump(mode='json')
        }
    except Exception as e:
        logger.error(f"Failed to load session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{year}/{gp}/{session_type}/track")
async def get_track_data(year: int, gp: str, session_type: str):
    """트랙 데이터 조회 (프론트엔드 맵용)"""
    try:
        fastf1_service.get_session(year, gp, session_type)
        track_data = fastf1_service.get_track_data()
        track_service.cache_track(track_data)

        # Canvas 렌더링용 포맷
        canvas_data = track_service.format_for_canvas(track_data)

        return {
            "success": True,
            "track": track_data.model_dump(mode='json'),
            "canvas": canvas_data
        }
    except Exception as e:
        logger.error(f"Failed to get track data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{year}/{gp}/{session_type}/laps")
async def get_laps(year: int, gp: str, session_type: str, driver: str = None):
    """랩 데이터 조회"""
    try:
        fastf1_service.get_session(year, gp, session_type)
        laps = fastf1_service.get_laps_data(driver)
        return {
            "success": True,
            "laps": [lap.model_dump(mode='json') for lap in laps]
        }
    except Exception as e:
        logger.error(f"Failed to get laps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{year}/{gp}/{session_type}/drivers")
async def get_drivers_summary(year: int, gp: str, session_type: str):
    """모든 드라이버 요약"""
    try:
        fastf1_service.get_session(year, gp, session_type)
        summaries = fastf1_service.get_all_drivers_summary()
        
        # FastF1 데이터가 없으면 모의 데이터 반환
        if not summaries:
            mock_drivers = [
                {"driver": "VER", "driver_code": "VER", "driver_number": 1, "driver_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_color": "#1E41FF", "position": 1, "total_laps": 53, "best_lap_time": 73.123, "compound_used": ["SOFT", "MEDIUM"]},
                {"driver": "PER", "driver_code": "PER", "driver_number": 11, "driver_name": "Sergio Perez", "team_name": "Red Bull Racing", "team_color": "#1E41FF", "position": 2, "total_laps": 53, "best_lap_time": 73.456, "compound_used": ["MEDIUM", "HARD"]},
                {"driver": "LEC", "driver_code": "LEC", "driver_number": 16, "driver_name": "Charles Leclerc", "team_name": "Ferrari", "team_color": "#E8002D", "position": 3, "total_laps": 53, "best_lap_time": 73.789, "compound_used": ["SOFT", "MEDIUM"]},
                {"driver": "SAI", "driver_code": "SAI", "driver_number": 55, "driver_name": "Carlos Sainz", "team_name": "Ferrari", "team_color": "#E8002D", "position": 4, "total_laps": 53, "best_lap_time": 74.012, "compound_used": ["MEDIUM", "HARD"]},
                {"driver": "HAM", "driver_code": "HAM", "driver_number": 44, "driver_name": "Lewis Hamilton", "team_name": "Mercedes", "team_color": "#27F4D2", "position": 5, "total_laps": 53, "best_lap_time": 74.345, "compound_used": ["SOFT", "MEDIUM"]},
                {"driver": "RUS", "driver_code": "RUS", "driver_number": 63, "driver_name": "George Russell", "team_name": "Mercedes", "team_color": "#27F4D2", "position": 6, "total_laps": 53, "best_lap_time": 74.678, "compound_used": ["MEDIUM", "HARD"]},
                {"driver": "NOR", "driver_code": "NOR", "driver_number": 4, "driver_name": "Lando Norris", "team_name": "McLaren", "team_color": "#FF8000", "position": 7, "total_laps": 53, "best_lap_time": 74.901, "compound_used": ["SOFT", "MEDIUM"]},
                {"driver": "PIA", "driver_code": "PIA", "driver_number": 81, "driver_name": "Oscar Piastri", "team_name": "McLaren", "team_color": "#FF8000", "position": 8, "total_laps": 53, "best_lap_time": 75.234, "compound_used": ["MEDIUM", "HARD"]},
                {"driver": "ALO", "driver_code": "ALO", "driver_number": 14, "driver_name": "Fernando Alonso", "team_name": "Aston Martin", "team_color": "#229971", "position": 9, "total_laps": 53, "best_lap_time": 75.567, "compound_used": ["SOFT", "MEDIUM"]},
                {"driver": "STR", "driver_code": "STR", "driver_number": 18, "driver_name": "Lance Stroll", "team_name": "Aston Martin", "team_color": "#229971", "position": 10, "total_laps": 53, "best_lap_time": 75.890, "compound_used": ["MEDIUM", "HARD"]},
            ]
            summaries = mock_drivers
        
        return {
            "success": True,
            "drivers": summaries
        }
    except Exception as e:
        logger.error(f"Failed to get drivers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/track/{circuit_key}/canvas")
async def get_track_canvas(circuit_key: int, width: int = 800, height: int = 600):
    """캔버스 렌더링용 트랙 데이터"""
    track_data = track_service.get_track_for_map(circuit_key)
    if not track_data:
        raise HTTPException(status_code=404, detail="Track not found")

    canvas_data = track_service.format_for_canvas(track_data, (width, height))
    return canvas_data


@app.get("/api/car/position")
async def get_car_position(circuit_key: int, x: float, y: float):
    """차량 위치를 트랙 진행도로 변환"""
    track_data = track_service.get_track_for_map(circuit_key)
    if not track_data:
        raise HTTPException(status_code=404, detail="Track not found")

    position = track_service.get_car_position_on_track(x, y, track_data)
    if not position:
        raise HTTPException(status_code=400, detail="Cannot calculate position")

    return position


# 드라이버 정적 정보 API
@app.get("/api/drivers")
async def get_all_drivers():
    """모든 드라이버 정보 (OpenF1에서 로드)"""
    if openf1_service:
        await openf1_service.fetch_driver_info_rest()
        return {
            "success": True,
            "drivers": openf1_service.driver_info
        }
    return {"success": False, "drivers": {}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
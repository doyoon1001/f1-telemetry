# F1 Real-time Telemetry Dashboard

실시간 F1 레이스 텔레메트리 대시보드 - 타이어, 랩타임, 섹터타임, 트랙 맵 위 실시간 차량 위치 시각화

## 🏗️ 아키텍처

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   OpenF1 API    │ ─────────────────▶ │   FastAPI Backend │
│  (Live Timing)  │   실시간 스트림     │  (FastF1 + WS)    │
└─────────────────┘                    └────────┬─────────┘
                                                 │
                          REST API + WebSocket  │
                                                 ▼
                                    ┌──────────────────┐
                                    │  React Frontend  │
                                    │ Leaflet + Canvas │
                                    └──────────────────┘
```

## 📁 프로젝트 구조

```
f1-telemetry/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트
│   │   ├── api/
│   │   │   ├── routes.py        # REST API 라우트
│   │   │   └── websocket.py     # WebSocket 핸들러
│   │   ├── services/
│   │   │   ├── fastf1_service.py    # FastF1 데이터 수집
│   │   │   ├── openf1_service.py    # OpenF1 WebSocket 클라이언트
│   │   │   └── track_service.py     # 트랙 데이터 변환
│   │   ├── models/
│   │   │   └── telemetry.py    # Pydantic 모델
│   │   └── core/
│   │       └── config.py       # 설정 관리
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TrackMap.jsx         # Leaflet + Canvas 트랙 맵
│   │   │   ├── CarMarker.jsx        # 차량 마커 (Canvas)
│   │   │   ├── TelemetryPanel.jsx   # 실시간 텔레메트리 패널
│   │   │   └── DriverList.jsx       # 드라이버 리스트
│   │   ├── hooks/
│   │   │   └── useTelemetry.js      # WebSocket 훅
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── scripts/
    └── init_cache.py
```

## 🚀 빠른 시작

### 1. 백엔드 실행
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### 2. 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
```

### 3. Docker로 전체 실행
```bash
docker-compose up -d
```

## 🔑 주요 기능

- ✅ 실시간 타이어 컴파운드 (SOFT/MEDIUM/HARD/INTER/WET)
- ✅ 실시간 랩타임 + 섹터별 타임 (S1/S2/S3)
- ✅ 트랙 맵 위 실시간 차량 위치 (Canvas 오버레이)
- ✅ 드라이버별 속도, 기어, DRS, 브레이크 상태
- ✅ 섹터 타임 비교 및 개인 최고 기록 하이라이트

## 📡 데이터 소스

| 소스 | 용도 |
|------|------|
| **FastF1** | 세션 메타데이터, 과거 랩 데이터, 트랙 레이아웃 |
| **OpenF1 WebSocket** | 실시간 텔레메트리 (위치, 속도, 타이어, 섹터타임) |

## 🛠️ 개발 환경

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
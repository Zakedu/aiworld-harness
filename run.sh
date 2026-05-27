#!/usr/bin/env bash
# AI World Harness — 원샷 실행 스크립트
# 최초 실행: 의존성 설치 + DB 초기화 + 서버 기동
# 두번째부터는: 서버 기동만

set -e
cd "$(dirname "$0")"

# 1. venv가 없으면 만들고 deps 설치
if [ ! -d "venv" ]; then
  echo "==> venv 생성 + 의존성 설치 (1회)"
  python3 -m venv venv
  ./venv/bin/pip install --upgrade pip > /dev/null
  ./venv/bin/pip install -r requirements.txt 'httpx[socks]'
fi

# 2. .env 체크
if [ ! -f ".env" ]; then
  echo "!! .env 가 없습니다. .env.example 을 복사한 뒤 API 키를 채우세요."
  exit 1
fi

# 3. DB 초기화 (이미 있으면 skip)
if [ ! -f "data/aiworld.db" ]; then
  echo "==> DB 초기화"
  ./venv/bin/python -m backend.db init
fi

# 4. 서버 기동
PORT="${PORT:-8080}"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '127.0.0.1')"

echo ""
echo "================================================================"
echo "  AI World Harness 기동 중..."
echo "  이 PC          : http://localhost:${PORT}"
echo "  사내 Wi-Fi     : http://${LAN_IP}:${PORT}"
echo ""
echo "  퍼블릭(인터넷) URL 만들려면 새 터미널에서:"
echo "    brew install --cask ngrok    # 1회만"
echo "    ngrok http ${PORT}"
echo "================================================================"
echo ""

exec ./venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}" \
  --reload --reload-include '*.env' --reload-include '*.yaml' --reload-include '*.json'

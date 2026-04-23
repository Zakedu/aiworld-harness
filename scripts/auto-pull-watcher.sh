#!/usr/bin/env bash
# AI World Harness — 원격 자동 반영 워처
#
# 목적: 원격 저장소(origin/main)에 새 커밋이 올라오면 자동으로 git pull.
#       uvicorn --reload 가 파일 변경을 감지해 서버를 재시작.
# 사용: 터미널 탭 1개 열어서 ./scripts/auto-pull-watcher.sh 실행.
#       서버(./run.sh)와 병렬로 계속 켜둔 채 두면 됨.

set -e
cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

# 환경변수로 조절 가능
INTERVAL="${INTERVAL:-30}"      # 폴링 주기(초)
BRANCH="${BRANCH:-main}"        # 추적할 원격 브랜치
SAFE_ONLY="${SAFE_ONLY:-1}"     # 1이면 로컬 변경 있을 때 pull 건너뜀

if [ ! -d ".git" ]; then
  echo "❌ git 저장소가 아님: $PROJECT_DIR"
  exit 1
fi
if ! git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  echo "❌ 브랜치 $BRANCH 없음"
  exit 1
fi
if ! git config --get remote.origin.url >/dev/null 2>&1; then
  echo "❌ origin remote 없음 — GitHub push 이후 실행"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AI World Harness — 자동 Pull Watcher                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  원격 브랜치:  origin/$BRANCH"
echo "║  폴링 주기:    ${INTERVAL}초"
echo "║  안전 모드:    $SAFE_ONLY (로컬 변경 감지 시 pull 생략)"
echo "║                                                          ║"
echo "║  로그:"
echo "║    🆕 = 새 커밋 감지"
echo "║    ✅ = pull 성공 (uvicorn 자동 재시작)"
echo "║    ⚠️  = 건너뜀 (로컬 변경·충돌)"
echo "║    ❌ = 오류"
echo "║                                                          ║"
echo "║  종료: Ctrl+C                                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

trap 'echo ""; echo "👋 워처 종료"; exit 0' INT TERM

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

while true; do
  if ! git fetch origin "$BRANCH" --quiet 2>/dev/null; then
    log "❌ fetch 실패 (네트워크·인증 확인)"
    sleep "$INTERVAL"
    continue
  fi

  LOCAL=$(git rev-parse "$BRANCH" 2>/dev/null || echo "local-missing")
  REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "remote-missing")
  BASE=$(git merge-base "$BRANCH" "origin/$BRANCH" 2>/dev/null || echo "no-base")

  if [ "$LOCAL" = "$REMOTE" ]; then
    # 변경 없음 — 조용히 대기
    :
  elif [ "$LOCAL" = "$BASE" ]; then
    # 원격이 앞서 있음 → fast-forward pull 가능
    log "🆕 새 커밋 감지 (원격이 앞섬)"

    if [ "$SAFE_ONLY" = "1" ]; then
      if ! git diff --quiet || ! git diff --cached --quiet; then
        log "⚠️  로컬에 커밋 안 된 변경사항 있음 — pull 건너뜀 (SAFE_ONLY=1)"
        log "    해결: git stash / git commit / SAFE_ONLY=0 으로 재시도"
        sleep "$INTERVAL"
        continue
      fi
    fi

    if git pull --ff-only origin "$BRANCH"; then
      log "✅ pull 완료 — uvicorn --reload 가 자동 재시작합니다"
      # 최근 커밋 1개 표시
      echo "    └─ $(git log -1 --format='%h %s (%an, %ar)')"
    else
      log "❌ pull 실패"
    fi
  elif [ "$REMOTE" = "$BASE" ]; then
    # 로컬이 앞서 있음 → 원격으로 push 대기 (여기선 건드리지 않음)
    :
  else
    # 양쪽 diverge — 수동 개입 필요
    log "⚠️  로컬과 원격이 갈라졌음 — 수동 병합 필요 (git pull --rebase 또는 merge)"
  fi

  sleep "$INTERVAL"
done

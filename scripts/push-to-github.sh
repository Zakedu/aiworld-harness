#!/usr/bin/env bash
# AI World Harness — GitHub 레포 생성 + 초기 커밋 + 푸시
# 안전장치: .env 절대 커밋되지 않도록 이중 확인

set -e
cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
echo "📁 프로젝트 디렉토리: $PROJECT_DIR"

# ─── 1. Git 설정 확인 ──────────────────────────────────────────
git config --global user.name >/dev/null 2>&1 || git config --global user.name "Jake Lee"
git config --global user.email >/dev/null 2>&1 || git config --global user.email "jinkyu.lee@day1company.co.kr"

# ─── 2. git init (필요 시) ────────────────────────────────────
if [ ! -d ".git" ]; then
  echo "🔧 git 저장소 초기화 (main 브랜치)"
  git init -b main
fi

# ─── 3. .env 안전 제외 (이중 확인) ────────────────────────────
grep -qxF ".env" .gitignore 2>/dev/null || echo ".env" >> .gitignore
# 혹시라도 이전에 추적됐다면 인덱스에서 제거
git rm --cached .env 2>/dev/null || true
echo "🔒 .env 는 항상 gitignore — 원격에 절대 올라가지 않음"

# ─── 4. 스테이징 + sanity check ───────────────────────────────
echo "📋 변경 스테이징..."
git add .

if git ls-files --cached | grep -E '(^|/)\.env$' > /dev/null; then
  echo "❌ 중단: .env 파일이 스테이징에 남아있음. 수동 정리 필요"
  echo "   git rm --cached .env"
  exit 1
fi
echo "✓ .env 안전 확인 완료"

# 커밋 대상 요약 (최대 30줄)
echo ""
echo "── 커밋 대상 (요약) ──"
git status --short | head -30
CHANGED_COUNT=$(git status --short | wc -l | tr -d ' ')
echo "   총 변경 ${CHANGED_COUNT}개"
echo ""

# ─── 5. 커밋 ──────────────────────────────────────────────────
if git diff --cached --quiet && ! git rev-parse HEAD >/dev/null 2>&1; then
  echo "ℹ️ 빈 상태 — 커밋 건너뜀"
elif git diff --cached --quiet; then
  echo "ℹ️ 변경 없음 — 커밋 건너뜀"
else
  git commit -m "AI World Harness v1.0 — 멀티모델 교차검증 AI 교육 콘텐츠 생성 시스템

핵심 기능
- Claude Opus 4.7 × GPT-5.4 교차검증 파이프라인
- 위인 멘토링 시뮬레이션 콘셉트
- 3-Screen UX (Control · Execution · Review) with 3-pane Review
- 78개 루브릭 항목 LLM-as-judge 검증
- 플래그 5종 분류(FACT/SCHEMA/BORDERLINE/SENSITIVE/CONSISTENCY) + 앵커 하이라이트
- 항목·챕터·컴포넌트 단위 재생성 with 사용자 피드백
- xlsx + 학습자료 docx export

재사용 자산
- design-library/ — 자동화 프로덕트 공통 UX 원칙·토큰·패턴·문서

스택
- FastAPI + SQLite + WebSocket
- Tailwind CDN + Pretendard + vanilla JS
- python-docx + openpyxl
"
  echo "✓ 커밋 완료"
fi

# ─── 6. GitHub 저장소 생성 + 푸시 ──────────────────────────────
if ! command -v gh >/dev/null 2>&1; then
  echo ""
  echo "⚠️  GitHub CLI (gh) 미설치"
  echo ""
  echo "옵션 A — gh 설치 (권장):"
  echo "    brew install gh"
  echo "    gh auth login"
  echo "    다시 이 스크립트 실행: ./scripts/push-to-github.sh"
  echo ""
  echo "옵션 B — 웹에서 수동:"
  echo "    1) https://github.com/new 에서 저장소 생성 (Private 권장, 이름: aiworld-harness)"
  echo "    2) 아래 명령 실행:"
  echo "       git remote add origin git@github.com:<USERNAME>/aiworld-harness.git"
  echo "       git push -u origin main"
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "🔐 GitHub 로그인 필요:"
  echo "    gh auth login"
  echo "로그인 후 다시 이 스크립트 실행."
  exit 1
fi

# 이미 origin 있으면 push만, 없으면 repo 생성 + push
if git remote | grep -qx 'origin'; then
  echo "ℹ️ 'origin' 원격이 이미 설정됨 — push 시도"
  git push -u origin main
else
  echo "🚀 GitHub 저장소 생성 + 푸시 (private)..."
  gh repo create aiworld-harness \
    --private \
    --source=. \
    --remote=origin \
    --push \
    --description "멀티모델 교차검증(Claude × GPT) 기반 AI 교육 콘텐츠 자동 생성 시스템. 위인 멘토링 시뮬레이션 · 루브릭 검증 · 플래그 재생성 루프"
fi

# ─── 7. 완료 메시지 ───────────────────────────────────────────
USER_NAME="$(gh api user --jq .login 2>/dev/null || echo '<USER>')"
echo ""
echo "✅ 완료"
echo "🔗 https://github.com/${USER_NAME}/aiworld-harness"
echo ""
echo "다음 작업 (원하면):"
echo "  - 프로젝트 설명/topics 추가: gh repo edit --add-topic automation,llm,korean"
echo "  - Collaborators 추가: gh api repos/${USER_NAME}/aiworld-harness/collaborators/<USERNAME> -X PUT"
echo "  - press-release-harness 를 별도 레포로 분리하려면:"
echo "     cd /Users/ga/Projects/press-release-harness && ./scripts/push-to-github.sh  (해당 스크립트 별도 생성 필요)"

# AI World Harness

> 위인 멘토링 시뮬레이션 기반 AI 교육 코스 자동 생성 시스템
> **멀티모델 교차검증(Claude Opus 4.7 ↔ GPT-5.4) · 로컬 서버 · SQLite · 사내 LAN 배포**

기존 `aiworld-main`(Claude Code 스킬 파이프라인)의 서식·기획 로직을 그대로 계승하고, 그 위에 멀티모델 교차검증·플래그 기반 사람 개입·항목 단위 재생성을 얹은 v2 시스템.

---

## Quick Start

```bash
# 0. Python 3.11+ 필요
python3 --version

# 1. 가상환경
cd aiworld_harness
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY / OPENAI_API_KEY 입력
# (이미 .env가 있으면 skip)

# 4. DB 초기화 (최초 1회)
python -m backend.db init

# 5. 서버 기동
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 접속

| 환경 | URL |
|---|---|
| 이 PC 자기자신 | http://localhost:8000 |
| 사내 Wi-Fi 다른 기기 | http://{이_PC의_IP}:8000 |

**이 PC의 IP 확인 (macOS)**
```bash
ipconfig getifaddr en0           # Wi-Fi 보통 en0, 유선이면 en1
# 또는
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**macOS 방화벽 허용**: "시스템 설정 → 네트워크 → 방화벽 → 옵션"에서 `Python` 또는 `uvicorn` 수신 연결 허용. 1회 설정.

---

## 프로젝트 구조

```
aiworld_harness/
├── backend/
│   ├── main.py              # FastAPI entrypoint (REST + WebSocket + static)
│   ├── config.py            # env 로드, 모델 매트릭스
│   ├── db.py                # SQLite 스키마 + 초기화
│   ├── orchestrator.py      # 파이프라인 제어 (기획 → 병렬 생성 → 검증 → 재생성)
│   ├── ws.py                # WebSocket 매니저
│   ├── agents/
│   │   ├── base.py          # Claude/OpenAI 통합 래퍼
│   │   ├── course_planner.py
│   │   ├── quiz_generator.py
│   │   └── practice_generator.py
│   └── validators/
│       ├── schema_validator.py   # 순수 Python (no LLM)
│       └── rubric_validator.py   # LLM-as-judge
├── frontend/
│   └── index.html           # 3-Screen SPA (Tailwind CDN + vanilla JS)
├── data/
│   ├── aiworld.db           # SQLite (자동 생성)
│   ├── schema-v1.json       # 컴포넌트 스키마 (aiworld-main 계승)
│   └── rubric-v1.yaml       # 평가 루브릭 (5개 과정 피드백 반영)
├── docs/
│   └── DESIGN.md            # 전체 설계서
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## 핵심 개념

### 1) 교차검증 매트릭스 (`backend/config.py`)

| 컴포넌트 | 생성자 | 검증자 |
|---|---|---|
| 과정 기획 | Claude Opus 4.7 | GPT-5.4 |
| 위인 선정 배경 | GPT-5.4 | Claude Opus 4.7 |
| 학습자료 | Claude Opus 4.7 | GPT-5.4 |
| 퀴즈 | GPT-5.4 | Claude Opus 4.7 |
| 실습 | Claude Opus 4.7 | GPT-5.4 |

### 2) 3-Screen UX

- **Screen 1 (Control)** — 자판기 UI: 위인·주제·학습대상·학습목표·분량 + 믹서 슬라이더(위인 활용 강도, 힌트 상세도, 검증 엄격도, 프롬프트 레벨) + 읽기전용 프리셋
- **Screen 2 (Execution)** — 실시간 생성·검증·재생성 흐름을 WebSocket으로 시각화. Director 기획서 → 사용자 승인 → 컴포넌트 병렬 생성
- **Screen 3 (Review)** — 플래그 5종(FACT/SCHEMA/BORDERLINE/SENSITIVE/CONSISTENCY) 필터 + 카드 단위 인라인 수정 지시 + 재생성 버튼

### 3) 재생성 시작·끝 지점

- **시작**: 플래그 카드의 "재생성" 버튼 (`POST /api/components/:id/regenerate-item`). 사용자가 수정 지시를 입력하면 같은 생성 모델이 **그 항목 1개만** 재생성 — 기획서·동일 챕터의 형제 항목·프리셋을 컨텍스트로 상속
- **끝**: (a) 재검증 통과 → 플래그 resolved · 새 버전 approved, (b) 재시도 3회 초과 → BORDERLINE 격상·사람 인라인 편집, (c) 사용자가 "무시하고 통과" → 즉시 종료

### 4) 5개 과정 피드백 반영

- 실습 문제에 구체 예시/맥락 필수 (단일 키워드 금지)
- 정답은 "프롬프트 good/better 예시" 형태 강제
- 힌트에 프롬프트 작성용 구체 예시 정보 필수
- 하 난이도 합격컷 0~55점 허용
- 테이블 서식 엄격 준수 (Schema validator가 차단)
- 학습자료의 "이런 적 있지 않나요" 공감 오프너 + SWOT/개념설명 + 상황별 복붙 템플릿 필수

모든 루브릭 항목은 `data/rubric-v1.yaml`에 YAML로 문서화.

---

## API 요약

### REST
- `POST /api/runs` — 새 run 시작
- `GET /api/runs/{run_id}` — 상태·컴포넌트·플래그 조회
- `POST /api/runs/{run_id}/approve-blueprint` — 기획서 승인 (Step 2 시작)
- `GET /api/components/{component_id}` — 컴포넌트 상세
- `POST /api/components/{component_id}/regenerate-item` — 항목 단위 재생성
- `POST /api/flags/{flag_id}/resolve` — 플래그 해결 (dismissed/inline_edited/approved)
- `GET /api/presets/{key}` — 프리셋 조회 (schema, rubric, tone, courseid_rule)

### WebSocket
- `WS /ws/runs/{run_id}` — 실시간 이벤트
  - `blueprint.started` / `blueprint.completed`
  - `component.generating` / `component.generated` / `component.validated` / `component.flagged` / `component.regenerating`
  - `run.completed`

---

## Phase 로드맵

| Phase | 상태 | 내용 |
|---|---|---|
| **Phase 0** | ✅ 완료 | 설계서·스키마·루브릭·프로젝트 스캐폴드 |
| **Phase 1 MVP** | 🔨 현재 | Director + 퀴즈·실습 에이전트 + Schema Validator + Rubric Validator + 3-Screen UI |
| **Phase 2** | 예정 | 학습자료(material-writer) + 위인 선정 배경 에이전트, 전 컴포넌트 교차검증 |
| **Phase 3** | 예정 | xlsx export, 챕터 단위 재생성, 컴포넌트 단위 재생성, 관리자 프리셋 편집 UI |
| **Phase 4** | 예정 | PoC 1과정 돌려서 루브릭·프롬프트·모델 매트릭스 재튜닝 |

---

## 보안 주의

- `.env`는 `.gitignore`에 포함되어 있음. **절대 커밋 금지.**
- 내부망 배포 수준의 인증은 MVP에 포함하지 않음. 외부 공유 필요 시 reverse proxy + basic auth 필수.
- 이 저장소를 외부에 공유하기 전에 `.env`에 담긴 **API 키는 반드시 Anthropic/OpenAI 콘솔에서 로테이트** 권장 (초기 세팅 중 대화로 전달받은 키는 로그에 남을 수 있음).

---

## Known Limitations / Next Steps

1. **학습자료 에이전트 미구현** (MVP에서는 프롬프트 기법 요약문으로 대체). Phase 2에서 `material_writer` 추가.
2. **퀴즈 item 단위 재생성 미구현** (실습만 지원). Phase 2에서 추가.
3. **xlsx export 미구현**. Phase 3에서 `openpyxl`로 기존 aiworld-main 템플릿 양식에 맞춰 출력 예정.
4. **관리자 프리셋 편집 UI 미구현**. 현재는 `data/*.yaml`/`*.json` 직접 편집.

---

*v1.0 · 2026-04-22*

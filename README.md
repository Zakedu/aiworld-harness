# AI World Harness

> "위인 멘토링 시뮬레이션" 기반 AI 교육 코스 자동 생성·검증 시스템
> **멀티모델 교차검증 (Claude Opus 4.7 생성 / GPT-5.4 검증) · 로컬 서버 · SQLite · 사내 LAN 배포**

위인(앤 설리번·제임스 본드·콜럼버스 등)을 멘토로 설정한 AI 프롬프트 교육 코스를 입력값 몇 개로부터 자동 생성하고, 생성자와 다른 모델이 교차 검증한 뒤, 사람이 플래그만 훑어서 최종 승인·수정할 수 있게 하는 파이프라인.

**한 번의 Run**으로 만들어지는 것:
- 과정 기획서 · 위인 선정 배경 · 학습자료 10챕터 · 퀴즈 100문항 · 실습 30문제
- 20~40분 · Claude·GPT 각각 수십 번 호출 · 약 $1~3 비용

---

## 목차

1. [Quick Start](#quick-start)
2. [협업자 온보딩 체크리스트](#협업자-온보딩-체크리스트)
3. [아키텍처](#아키텍처)
4. [3-Screen UX](#3-screen-ux)
5. [에이전트 · 프롬프트](#에이전트--프롬프트)
6. [검증 시스템](#검증-시스템)
7. [API 레퍼런스](#api-레퍼런스)
8. [프로젝트 구조](#프로젝트-구조)
9. [Export](#export)
10. [재생성 루프](#재생성-루프)
11. [Admin 페이지](#admin-페이지)
12. [Design Library](#design-library)
13. [Contributing](#contributing)

---

## Quick Start

### 사전 요구사항
- **Python 3.9+** (3.10+ 권장)
- **Node/npm 불필요** — 프론트엔드는 Tailwind CDN + vanilla JS
- Anthropic API 키 · OpenAI API 키

### 설치 및 실행

```bash
# 1. clone
git clone https://github.com/Zakedu/aiworld-harness.git
cd aiworld-harness

# 2. venv + deps (최초 1회)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 환경변수
cp .env.example .env
# .env 열어서 ANTHROPIC_API_KEY / OPENAI_API_KEY 입력

# 4. 실행 (원샷 스크립트 — 의존성·DB 초기화·서버 기동까지)
chmod +x run.sh
./run.sh
```

### 접속 URL

| 환경 | URL |
|---|---|
| 이 PC 자기자신 | http://localhost:8000 |
| 사내 Wi-Fi 다른 기기 | http://{이 PC의 IP}:8000 |

**내부 IP 확인** (macOS): `ipconfig getifaddr en0` → Wi-Fi · `en1` → 유선
**macOS 방화벽**: "시스템 설정 → 네트워크 → 방화벽"에서 `Python` 수신 허용 1회

---

## 협업자 온보딩 체크리스트

처음 기여하는 분을 위한 필수 단계:

- [ ] 이 레포에 **Collaborator 권한** 받기 (Repository owner → Settings → Access)
- [ ] 로컬에 clone · venv 세팅 · `./run.sh`로 정상 부팅 확인
- [ ] 본인 API 키로 `.env` 구성 (공유된 키 사용 금지 — 사용량·비용 추적)
- [ ] 브라우저에서 Control 탭 열고 **샘플 run 1개** 돌려보기 (~20분, ~$1)
- [ ] `design-library/principles.md` 읽기 (자동화 프로덕트 UX 8원칙)
- [ ] **main 브랜치 직접 push 금지** — 반드시 feature 브랜치 + PR
- [ ] PR 시 요약·스크린샷 첨부 권장

### 자주 쓰는 기여 포인트
- **프롬프트 다듬기**: `backend/agents/*.py` 의 `SYSTEM_PROMPT` 수정 (또는 UI의 Admin 페이지에서 로컬 override)
- **새 루브릭 항목**: `data/rubric-v1.yaml` + `backend/validators/schema_validator.py` 자동 규칙 쌍으로 추가
- **UI 개선**: `frontend/index.html` (단일 파일, Tailwind + vanilla JS)
- **새 컴포넌트 타입**: agent 1개 · schema 정의 · rubric 섹션 · 프론트 preview 렌더러 4곳 수정 필요

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (index.html · Tailwind CDN · Pretendard · vanilla) │
│  Sidebar · Top bar · Stepper · 4 Tabs                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────┴─────────────────────────────────────┐
│  FastAPI Backend (Python 3.9+)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Orchestrator — Director → 위인배경 → 학습자료 → 퀴즈·실습 │  │
│  │ 각 단계 교차검증 + 자동 재시도 3회                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────┐   ┌──────────────────────────┐   │
│  │ Generators (Claude)  │   │ Validators (GPT-5.4)     │   │
│  │ - course_planner     │   │ - schema (코드)          │   │
│  │ - figure_rationale   │   │ - rubric (LLM-as-judge)  │   │
│  │ - material_writer    │   │   × 컴포넌트 타입별 5종  │   │
│  │ - quiz_generator     │   │                          │   │
│  │ - practice_generator │   │                          │   │
│  └──────────────────────┘   └──────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SQLite (data/aiworld.db) · 8 tables · WAL mode       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Exporters · xlsx (openpyxl) · docx (python-docx)     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        ↕
      Anthropic API (Claude Opus 4.7) / OpenAI API (GPT-5.4)
```

---

## 3-Screen UX

### Screen 1 · Control (새 코스 만들기)
3개 카드 스택으로 설정 입력:
- **① 코스 입력** (필수) — 위인 · 주제 · 학습 대상 · 학습 목표 · 카테고리 · 챕터 구성(파트×챕터) · 예상 학습 시간
  - 카테고리는 6종 프리셋 + "기타: 직접 입력" 지원
- **② 결과값 조절** — 위인 활용 강도 · 힌트 상세도 · 검증 엄격도 · 프롬프트 예시 · 난이도 프리셋(입문/일반/고급) · 퀴즈/실습 수량 · 타깃 AI 도구
- **③ 고정 프리셋** (관리자만) — 서식 버전·톤앤매너·courseId 규칙·루브릭 (읽기전용)

### Screen 2 · Execution (진행 상황)
- **Stats Bar** — 위인배경 / 학습자료 / 퀴즈 / 실습 / 플래그 카운트
- **Director 카드** — 3-state (idle / loading skeleton / editable form)
- **Kanban 뷰** — 생성중 / 검증중 / 통과 / 플래그 4컬럼, WebSocket 실시간
- **Event Log** — 접이식, 색상 코딩

### Screen 3 · Review (검토 & 승인)
**3-Pane** (드래그 divider로 폭 조정 가능, localStorage에 저장):
- **좌 · Navigator** — 커리큘럼 트리 + 플래그 카운트 배지 + 상태 라벨
- **중 · Content Preview** — 타입별 렌더 (material 섹션 6개 / quiz 10문항 / practice 3문제 / figure_rationale 스토리텔링)
  - 퀴즈 해설은 **정답이유 / 오답피드백 / 실무팁** 3-column 라벨 카드
- **우 · Flag Panel** — 카테고리 필터 5종 + 플래그 카드 (위치·사유·가이드·수정지시 textarea·재생성·무시)
  - 플래그 클릭 시 중앙 프리뷰의 해당 영역으로 `⚐ 여기` 앵커 + 노란 하이라이트

**키보드 단축키**: `↑↓ j k` 카드 이동 · `R` 재생성 · `D` 무시

### Admin (환경설정) · 신규
- 환경 요약 (모델 · API 키 마스킹 · CROSS_MATRIX · 재시도 상한)
- **10개 시스템 프롬프트 열람·편집** (생성자 5 + 검증자 5)
- DB override 저장 → 다음 LLM 호출부터 즉시 반영
- "기본값으로 재설정"으로 코드 원본 복귀

---

## 에이전트 · 프롬프트

### 생성자 (Claude Opus 4.7 · 5종)
| 에이전트 | 파일 | 역할 |
|---|---|---|
| `course_planner` | `backend/agents/course_planner.py` | Director — 코스 기획서 (커리큘럼 10챕터) |
| `figure_rationale` | `backend/agents/figure_rationale.py` | 위인 선정 배경 1건 (배경·철학·주제 적합성·에피소드) |
| `material_writer` | `backend/agents/material_writer.py` | 챕터별 학습자료 (6섹션 · Bad/Good/Better 3단) |
| `quiz_generator` | `backend/agents/quiz_generator.py` | 챕터당 10문항 (5유형 × 2) |
| `practice_generator` | `backend/agents/practice_generator.py` | 챕터당 3문제 (실험·레슨·도전) |

### 검증자 (GPT-5.4 · 5종) — 컴포넌트별 고유 평가 기준
| 검증자 | 특화 평가 관점 |
|---|---|
| `validator_course_overview` | 네이밍 패턴 · 수강대상/효과 구체성 · 기법 중복 · 위인-주제 연결성 |
| `validator_figure_rationale` | 사실 기반 · 출처 명시 · 실무 행동 · 멘토 톤 |
| `validator_material` | 6섹션 구조 · Bad/Good/Better · 소제목 고정 · 이모지 · 표 · 뻔한 이야기 엄격 |
| `validator_quiz` | 유형별 정답 형식 · 어미 규칙 · 파이프 3단 해설 · 이해 중심 |
| `validator_practice` | 3단계 순서 · 길이 40~100/94~140 · 제목 자가완결성 · 정답 프롬프트 형식 |

프롬프트는 **하드코딩 기본값 + DB 오버라이드** 2층 구조 (`backend/prompts_store.py`):
1. 코드 기본값: `*.py`의 `SYSTEM_PROMPT` (git으로 공유)
2. 오버라이드: `presets` 테이블에 저장 (로컬 전용, Admin 페이지에서 편집)

### 교차검증 매트릭스 (`backend/config.py`)
```python
CROSS_MATRIX = {
    "course_overview":   ("claude", "openai"),
    "figure_rationale":  ("claude", "openai"),
    "material":          ("claude", "openai"),
    "quiz":              ("claude", "openai"),
    "practice":          ("claude", "openai"),
}
```

v1.1 기준 **모든 생성자 = Claude, 모든 검증자 = GPT**로 단순화. 컴포넌트별 차별은 프롬프트에서.

---

## 검증 시스템

### 3단 검증
1. **Schema Validator** (코드, `backend/validators/schema_validator.py`) — LLM 불필요
   - JSON Schema 필드 타입·enum·required
   - 자동 규칙: 퀴즈 유형·보기 개수·분류 완전분배·단답형 초성 / 실습 길이(title 40~100자 · description 94~140자 · criteria ≤20/40자) · 평가항목 중복 · 고정값 · 학습자료 Bad/Good/Better·소제목·표·이모지 등
2. **Rubric Validator** (LLM-as-judge, `backend/validators/rubric_validator.py`)
   - `data/rubric-v1.yaml`의 **78개 항목**을 컴포넌트 타입별로 PASS/MARGINAL/FAIL 판정
   - 각 항목에 `severity_if_fail` (상/중/하)
   - 점수 80점 이하면 재생성 루프 진입
3. **Consistency** (향후 확장) — 챕터 간·버전 간 일관성

### 플래그 카테고리 5종
| 카테고리 | 한글 라벨 | 의미 |
|---|---|---|
| `FACT` | 출처·사실 확인 | 위인 어록·통계·인명·날짜 팩트 의심 |
| `SCHEMA` | 서식 오류 | 자동 규칙 위반 (루프 한도 초과) |
| `BORDERLINE` | 애매함 — 사람 확인 | LLM 판정이 PASS/FAIL 경계 |
| `SENSITIVE` | 민감 표현 가능 | 일반화·편향·정치·법적 이슈 |
| `CONSISTENCY` | 앞뒤 불일치 | 기획서 vs 컴포넌트, 챕터 간 모순 |

---

## API 레퍼런스

### Runs
- `POST /api/runs` — 새 run 시작 (Tier 1 입력값 body)
- `GET /api/runs` — run 목록 (사이드바용)
- `GET /api/runs/{run_id}` — 상세 (components + flags)
- `GET /api/runs/{run_id}/summary` — 통계 (stats bar용)
- `DELETE /api/runs/{run_id}` — 삭제 (관련 테이블 cascade)
- `POST /api/runs/{run_id}/approve-blueprint` — 기획서 승인 (+ 수정 content 포함)

### Components · Flags
- `GET /api/components/{component_id}` — 상세 + flags + validation
- `POST /api/components/{component_id}/regenerate-item` — 항목 단위 재생성
- `POST /api/runs/{run_id}/chapters/{chapter_id}/regenerate` — 챕터 단위 재생성 (피드백 + 컴포넌트 선택)
- `POST /api/flags/{flag_id}/resolve` — dismissed · inline_edited · approved
- `POST /api/flags/bulk-resolve` — 벌크 해결

### Export
- `GET /api/runs/{run_id}/export.xlsx` — 7개 탭 xlsx (설정·개요·커리큘럼·위인선정배경·퀴즈·실습·학습자료 요약)
- `GET /api/runs/{run_id}/export.zip` — xlsx + 학습자료 docx 10개 번들
- `GET /api/components/{component_id}/export.docx` — 학습자료 1챕터 docx

### Admin
- `GET /api/admin/config` — 모델·API 키(마스킹)·CROSS_MATRIX·재시도 상한
- `GET /api/admin/prompts` — 10개 프롬프트 상태 (generator 5 + validator 5)
- `PUT /api/admin/prompts/{agent}` — 프롬프트 override 저장
- `DELETE /api/admin/prompts/{agent}` — 기본값 복귀

### WebSocket
- `WS /ws/runs/{run_id}` — 실시간 이벤트
  - `blueprint.started` / `.completed` / `.error`
  - `component.generating` / `.generated` / `.validated` / `.flagged` / `.regenerating` / `.error`
  - `chapter.regen_started` / `.regen_completed` / `.regen_error`
  - `run.completed`

---

## 프로젝트 구조

```
aiworld-harness/
├── README.md                          ← 이 문서
├── run.sh                             # 원샷 실행 스크립트
├── requirements.txt
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py                        # FastAPI entry · REST · WebSocket · static
│   ├── config.py                      # env · CROSS_MATRIX
│   ├── db.py                          # SQLite 스키마 · init_db()
│   ├── orchestrator.py                # 파이프라인 제어 · 재생성 루프
│   ├── ws.py                          # WebSocket 매니저
│   ├── prompts_store.py               # 프롬프트 override resolve (DB 기반)
│   ├── agents/
│   │   ├── base.py                    # Claude/OpenAI 통합 LLM 클라이언트
│   │   ├── course_planner.py
│   │   ├── figure_rationale.py
│   │   ├── material_writer.py
│   │   ├── quiz_generator.py
│   │   └── practice_generator.py
│   ├── validators/
│   │   ├── schema_validator.py        # 코드 자동 규칙 (LLM X)
│   │   └── rubric_validator.py        # LLM-as-judge + 컴포넌트별 5종 프롬프트
│   └── exporters/
│       ├── xlsx_export.py             # openpyxl
│       ├── docx_export.py             # python-docx (학습자료)
│       └── zip_export.py              # xlsx + docx 번들
│
├── frontend/
│   └── index.html                     # 단일 파일 SPA · Tailwind CDN · Pretendard · vanilla JS
│
├── data/
│   ├── aiworld.db                     # SQLite (gitignore) · 자동 생성
│   ├── schema-v1.json                 # 컴포넌트 JSON Schema
│   ├── rubric-v1.yaml                 # 78개 평가 항목 (material 25+ · quiz 24 · practice 22 · figure 6 · overview 7)
│   └── goldens/                       # few-shot 샘플 (콜럼버스 BestPractice 등)
│
├── docs/
│   └── DESIGN.md                      # 전체 아키텍처 설계 문서
│
├── design-library/                    # ⭐ 재사용 가능 UX/UI 자산
│   ├── README.md
│   ├── principles.md                  # 자동화 프로덕트 UX 8원칙
│   ├── 00-foundation/
│   │   ├── tokens.json                # 색·타이포·간격 토큰 (코드 import용)
│   │   └── tokens.md
│   ├── 01-components/
│   │   └── component-catalog.md
│   ├── 02-patterns/                   # 8개 패턴 (flag-anchor, regen, kanban 등)
│   ├── 03-screens-reference.md
│   ├── 04-flows-reference.md
│   ├── 05-state-matrix.md
│   ├── 06-content-voice.md
│   ├── 07-a11y-and-specs.md
│   ├── 08-governance.md
│   └── instances/
│       ├── _template/                 # 새 프로젝트 복사용
│       └── aiworld-harness/           # 이 프로젝트 고유 문서
│
└── scripts/
    ├── push-to-github.sh              # 초기 레포 생성 + 첫 커밋·푸시
    └── auto-pull-watcher.sh           # 원격 push 감지 → 자동 pull → uvicorn 재시작
```

---

## Export

### xlsx (주 산출물, 7개 탭)
`GET /api/runs/{id}/export.xlsx` 또는 UI의 상단 `xlsx 다운로드` 버튼
- 설정 / 개요 / 커리큘럼 / 위인 선정 배경 / 퀴즈(12컬럼 100문항) / 실습(18컬럼 30문제) / 학습자료 요약

### docx (학습자료 챕터별)
- **개별**: Review에서 material 컴포넌트 선택 → 헤더 `.docx` 버튼
- **번들**: `GET /api/runs/{id}/export.zip` → xlsx + docx 10개

---

## 재생성 루프

### 3가지 Scope
| Scope | 트리거 | 컨텍스트 상속 |
|---|---|---|
| **item** | 플래그 카드 "재생성" 버튼 (가장 빈번) | 기획서 + 형제 항목 + 프리셋 + 사용자 수정 지시 |
| **chapter** | 프리뷰 헤더 "이 챕터 전체 재생성" 버튼 | 기획서 + 이전 버전 + 사용자 피드백. material→quiz→practice 순차 |
| **component** | (관리자, 전 챕터의 특정 타입 재생성) | 기획서 + 루브릭 |

### 종료 조건
- ✅ 재검증 통과 → 새 버전 approved
- ⚠️ 재시도 상한(기본 3회) 도달 → BORDERLINE 격상, 사람 인라인 편집 유도
- ↩️ 사용자 "무시하고 통과" → 즉시 종료

---

## Admin 페이지

사이드바 **환경설정** 탭. 3개 카드:

1. **환경 설정** (읽기전용) — Claude/OpenAI 모델명 · API 키 마스킹(`sk-ant-api...1wAA`) · 재시도 상한 · 합격선 · 서버 주소
2. **교차검증 매트릭스** — 컴포넌트 × 생성자/검증자 5행 테이블
3. **에이전트 시스템 프롬프트** — 2그룹(Generators · Validators) × 5개 아코디언
   - 각 카드: 라벨 · key · 글자수 · 기본값/Override 배지
   - 펼치면 textarea + 저장/재설정/복사 버튼
   - Override 적용 중이면 하단에 "코드 기본값 보기" 접힘

**사용 시나리오**: "어떤 챕터는 위인 말투고 어떤 챕터는 아닌데 이유가 뭐지?" → Admin → material_writer 프롬프트 확인 → 위인 일관성 규칙 강화 → 저장 → 해당 챕터 재생성으로 비교

---

## Design Library

`design-library/` 폴더는 **다른 자동화 프로덕트 만들 때 재사용 가능한** UX/UI 자산. AI World Harness 구축 과정에서 추출됨.

**새 자동화 프로젝트 시작 시**:
1. `design-library/principles.md` 8원칙 점검
2. `00-foundation/tokens.json` 그대로 import
3. `02-patterns/` 중 필요한 것만 채택 (flag-anchor · kanban · regeneration 루프 등)
4. `instances/_template/` 복사해 프로젝트 고유 파일 생성

---

## Contributing

### 일반 워크플로
```bash
# 1. feature 브랜치
git checkout -b feature/my-change

# 2. 로컬에서 변경 + 테스트
# ... 코드 수정 ...
./run.sh  # 브라우저에서 확인

# 3. 커밋 + push
git add .
git commit -m "설명: 무엇을 왜"
git push origin feature/my-change

# 4. GitHub에서 PR 생성 → 리뷰 요청
```

### main 자동 반영 (owner PC에만)
owner(Jake) PC에서는 `./scripts/auto-pull-watcher.sh`가 30초마다 `origin/main` 감지 → 자동 `git pull` → `uvicorn --reload` 자동 재시작.
→ PR이 merge되면 곧 owner 머신에 반영됨.

### 커밋 규칙 (권장)
- 제목 한 줄 (50자 내) + 본문 (왜, 무엇을, 영향)
- 타입 prefix: `fix:`, `feat:`, `refactor:`, `docs:`, `style:`
- 한글 OK

### 테스트 (MVP 시점)
자동 테스트는 아직 없음. 변경 후 체크리스트:
- [ ] `./run.sh` 정상 부팅
- [ ] 샘플 run 1회 돌려 기본 흐름 확인
- [ ] Admin에서 프롬프트 현재값 확인 (override 걸려 있는지)
- [ ] 큰 프롬프트 수정 시: 이전 run 챕터 하나 재생성으로 품질 변화 spot-check

### 주의
- `.env` 절대 커밋 금지 (.gitignore 이중 안전장치 있지만 한 번 더 확인)
- SQLite DB(`data/aiworld.db`)는 로컬 전용, 공유 금지
- Admin에서 저장한 프롬프트 override도 로컬 DB 전용 (git 무관)

---

## 보안 주의

- `.env`는 `.gitignore`에 포함. **절대 커밋 금지.**
- 이 저장소는 **Private** (외부 노출 금지)
- 내부망 배포 수준의 인증은 MVP 비포함. 외부 공유 필요 시 reverse proxy + basic auth 필수.
- 사내 Wi-Fi 공유 시 방화벽·IP 제한 고려.

---

## 로드맵 (현재 상태)

- ✅ 파이프라인 전체 작동 (5개 컴포넌트 타입 × 교차검증)
- ✅ 3-Screen UX · 3-pane Review · 앵커 하이라이트 · 재생성 루프 (item·chapter)
- ✅ Admin 페이지 (10개 프롬프트 편집)
- ✅ xlsx · docx export · 챕터별 개별 다운로드
- ✅ Design Library 재사용 자산
- ✅ 자동 pull 워처
- 🔨 PoC 1과정 돌려서 루브릭·프롬프트 재튜닝
- 📋 예정: 컴포넌트 단위 재생성 UI · 보일러플레이트 라이브러리 · 엠바고 처리 · 기자 QA 생성 (→ press-release-harness로 분리 예정)
- 📋 예정: 자동 테스트 · GitHub Actions CI · Webhook 기반 즉시 반영

---

## 라이선스 · 크레딧

- 내부 사용 목적으로 작성됨. 외부 배포·상용화 시 라이선스 별도 합의.
- 원조 로직: `aiworld-main` (Claude Code 스킬 파이프라인) 계승
- 아키텍처 설계 · 구현: Jake (전략기획 팀장) + Claude

---

*v1.1 · 2026-04-23*

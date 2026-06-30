# AI World Harness

> "위인 멘토링 시뮬레이션" 기반 AI 교육 코스 자동 생성·검증 시스템
> **멀티모델 교차검증 (Claude Opus 4.7 생성 / GPT-5.4 검증) · 로컬 서버 · SQLite · 사내 LAN 배포**

위인(앤 설리번·제임스 본드·콜럼버스 등)을 멘토로 설정한 AI 프롬프트 교육 코스를 입력값 몇 개로부터 자동 생성하고, 생성자와 다른 모델이 교차 검증한 뒤, 사람이 플래그만 훑어서 최종 승인·수정할 수 있게 하는 파이프라인.

**한 번의 Run**으로 만들어지는 것:
- 과정 기획서 · 위인 선정 배경 · 스토리 · 학습자료 10챕터 · 퀴즈 100문항 · 실습 30문제 · 스페셜 퀴즈
- 20~40분 · Claude·GPT 각각 수십 번 호출 · 약 $1~3 비용

---

## 목차

1. [Quick Start](#quick-start)
2. [협업자 온보딩 체크리스트](#협업자-온보딩-체크리스트)
3. [아키텍처](#아키텍처)
4. [5-Tab UX](#5-tab-ux)
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
# 1. clone (v2.0 브랜치)
git clone -b v2.0 https://github.com/Zakedu/aiworld-harness.git
cd aiworld-harness

# 2. venv + deps (최초 1회)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 환경변수
cp .env.example .env
# .env 열어서 ANTHROPIC_API_KEY / OPENAI_API_KEY 입력
# 또는 서버 실행 후 환경설정 탭에서 UI로 직접 입력 가능

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
- [ ] 본인 API 키로 `.env` 구성 (또는 환경설정 탭 UI에서 입력)
- [ ] 브라우저에서 Control 탭 열고 **샘플 run 1개** 돌려보기 (~20분, ~$1)
- [ ] `design-library/principles.md` 읽기 (자동화 프로덕트 UX 8원칙)
- [ ] **main 브랜치 직접 push 금지** — 반드시 feature 브랜치 + PR

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
│  Sidebar · Header · Stepper · 5 Tabs · 다크/라이트 모드      │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────┴─────────────────────────────────────┐
│  FastAPI Backend (Python 3.9+)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Orchestrator — 기획 → 위인배경 → 스토리 → 학습자료    │  │
│  │              → 퀴즈·스페셜퀴즈·실습                   │  │
│  │ 교차검증 + 자동 재시도 3회 + 재검증 일괄 실행         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────┐   ┌──────────────────────────┐   │
│  │ Generators (Claude)  │   │ Validators (GPT-5.4)     │   │
│  │ - course_planner     │   │ - schema (코드)          │   │
│  │ - figure_rationale   │   │ - rubric (LLM-as-judge)  │   │
│  │ - story_writer ✨    │   │ - glossary ✨            │   │
│  │ - material_writer    │   │   × 컴포넌트 타입별       │   │
│  │ - quiz_generator     │   │                          │   │
│  │ - special_quiz ✨    │   │                          │   │
│  │ - practice_generator │   │                          │   │
│  └──────────────────────┘   └──────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SQLite (data/aiworld.db) · 8 tables · WAL mode       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Exporters · xlsx · sql ✨ · html ✨ · docx           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        ↕
      Anthropic API (Claude Opus 4.7) / OpenAI API (GPT-5.4)
```

---

## 5-Tab UX

### Tab 1 · Control (새 코스 만들기)
3개 카드 스택으로 설정 입력:
- **① 코스 입력** (필수) — 위인 · 주제 · 학습 대상 · 학습 목표 · 카테고리 · 챕터 구성 · 예상 학습 시간
- **② 결과값 조절** — 위인 활용 강도 · 힌트 상세도 · 검증 엄격도 · 프롬프트 예시 · 난이도 · 퀴즈/실습 수량
- **③ 고정 프리셋** (관리자만) — 서식 버전·톤앤매너·루브릭 (읽기전용)

### Tab 2 · Execution (진행 상황)
- **Stats Bar** — 생성/검증/통과/플래그 카운트 1행 표시
- **Director 카드** — 3-state (idle / loading / editable form)
- **Kanban 뷰** — 생성중 / 검증중 / 통과 / 플래그 4컬럼, WebSocket 실시간
- **Event Log** — 접이식, 색상 코딩

### Tab 3 · Review (검토 & 승인)
**3-Pane** (드래그 divider로 폭 조정 가능):
- **좌 · Navigator** — 커리큘럼 트리 + 플래그 카운트 배지 + 상태 라벨
- **중 · Content Preview** — 타입별 렌더 (material·quiz·practice·figure_rationale·story)
- **우 · Flag Panel** — 카테고리 필터 6종 + 플래그 카드 (수정지시·재생성·무시)
  - **검증 재실행** 버튼: `validation_error` / `generated` 상태 컴포넌트 일괄 재검증 ✨

**키보드 단축키**: `↑↓` 카드 이동 · `R` 재생성 · `D` 무시

### Tab 4 · Deploy (배포) ✨
검토 완료 후 파일 다운로드:
- **xlsx** — 콘텐츠 검수용 스프레드시트 (설정·개요·커리큘럼·위인배경·퀴즈·실습·학습자료)
- **SQL** — DB 직접 삽입용 INSERT 파일 (quiz / practice / course_practice_quiz 3테이블)

### Tab 5 · Admin (환경설정)
- **환경 설정** — 모델·API 키 마스킹·CROSS_MATRIX·서버 정보
- **API 키 변경** ✨ — Anthropic/OpenAI 키를 UI에서 직접 입력·저장 (`.env` 자동 업데이트)
- **교차검증 매트릭스** — 컴포넌트 × 생성자/검증자 테이블
- **에이전트 시스템 프롬프트** — 10개 아코디언 편집

---

## 에이전트 · 프롬프트

### 생성자 (Claude Opus 4.7 · 7종)
| 에이전트 | 파일 | 역할 |
|---|---|---|
| `course_planner` | `backend/agents/course_planner.py` | Director — 코스 기획서 |
| `figure_rationale` | `backend/agents/figure_rationale.py` | 위인 선정 배경 |
| `story_writer` | `backend/agents/story_writer.py` | 챕터별 위인 스토리 ✨ |
| `material_writer` | `backend/agents/material_writer.py` | 학습자료 (6섹션) |
| `quiz_generator` | `backend/agents/quiz_generator.py` | 퀴즈 (5유형) |
| `special_quiz_generator` | `backend/agents/special_quiz_generator.py` | 스페셜 퀴즈 ✨ |
| `practice_generator` | `backend/agents/practice_generator.py` | 실습 문제 |

### 검증자 (GPT-5.4)
| 검증자 | 특화 평가 관점 |
|---|---|
| `validator_course_overview` | 네이밍·수강대상·효과 구체성·위인-주제 연결성 |
| `validator_figure_rationale` | 사실 기반·출처 명시·멘토 톤 |
| `validator_material` | 6섹션 구조·Bad/Good/Better·소제목·이모지·표 |
| `validator_quiz` | 유형별 정답 형식·어미·해설 |
| `validator_practice` | 3단계 순서·길이·제목 자가완결성 |
| `glossary_validator` | 표준 용어 일치 여부 (glossary.yaml 기반) ✨ |

### 교차검증 매트릭스 (`backend/config.py`)
```python
CROSS_MATRIX = {
    "course_overview":   ("claude", "openai"),
    "figure_rationale":  ("claude", "openai"),
    "material":          ("claude", "openai"),
    "story":             ("claude", "openai"),
    "quiz":              ("claude", "openai"),
    "special_quiz":      ("claude", "openai"),
    "practice":          ("claude", "openai"),
}
```

---

## 검증 시스템

### 3단 검증
1. **Schema Validator** (코드) — JSON Schema 필드 타입·enum·required·자동 규칙
2. **Rubric Validator** (LLM-as-judge) — `data/rubric-v1.yaml` 항목별 PASS/MARGINAL/FAIL 판정
3. **Glossary Validator** ✨ — `data/glossary.yaml` 표준 용어 불일치 감지

### 플래그 카테고리 6종
| 카테고리 | 한글 라벨 | 의미 |
|---|---|---|
| `FACT` | 출처·사실 확인 | 어록·통계·인명·날짜 팩트 의심 |
| `SCHEMA` | 서식 오류 | 자동 규칙 위반 (루프 한도 초과) |
| `BORDERLINE` | 애매함 — 사람 확인 | LLM 판정이 PASS/FAIL 경계 |
| `SENSITIVE` | 민감 표현 가능 | 일반화·편향·정치·법적 이슈 |
| `CONSISTENCY` | 앞뒤 불일치 | 기획서 vs 컴포넌트, 챕터 간 모순 |
| `GLOSSARY` | 용어 불일치 | glossary.yaml 표준 용어 불일치 ✨ |

### 검증 재실행 ✨
Review 탭 우상단 "검증 재실행" 버튼 → `validation_error` + `generated` 상태 컴포넌트 전체를 새 키로 일괄 재검증.

---

## API 레퍼런스

### Runs
- `POST /api/runs` — 새 run 시작
- `GET /api/runs` — run 목록
- `GET /api/runs/{run_id}` — 상세
- `GET /api/runs/{run_id}/summary` — 통계
- `DELETE /api/runs/{run_id}` — 삭제
- `POST /api/runs/{run_id}/approve-blueprint` — 기획서 승인
- `POST /api/runs/{run_id}/revalidate` ✨ — 미검증 컴포넌트 일괄 재검증

### Components · Flags
- `GET /api/components/{component_id}` — 상세 + flags + validation
- `POST /api/components/{component_id}/regenerate-item` — 항목 단위 재생성
- `POST /api/runs/{run_id}/chapters/{chapter_id}/regenerate` — 챕터 단위 재생성
- `POST /api/flags/{flag_id}/resolve` — dismissed · inline_edited · approved
- `POST /api/flags/bulk-resolve` — 벌크 해결

### Export
- `GET /api/runs/{run_id}/export.xlsx` — xlsx (설정·개요·커리큘럼·위인배경·퀴즈·실습·학습자료)
- `GET /api/runs/{run_id}/export.sql` ✨ — INSERT SQL (quiz / practice / course_practice_quiz)
- `GET /api/runs/{run_id}/export.zip` — xlsx + 학습자료 docx 번들
- `GET /api/components/{component_id}/export.docx` — 학습자료 1챕터 docx

### Admin
- `GET /api/admin/config` — 모델·API 키(마스킹)·CROSS_MATRIX
- `POST /api/admin/api-key` ✨ — API 키 `.env` 업데이트 (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`)
- `GET /api/admin/prompts` — 프롬프트 목록
- `PUT /api/admin/prompts/{agent}` — 프롬프트 override 저장
- `DELETE /api/admin/prompts/{agent}` — 기본값 복귀

### WebSocket
- `WS /ws/runs/{run_id}` — 실시간 이벤트
  - `blueprint.started / .completed / .error`
  - `component.generating / .generated / .validated / .flagged / .regenerating / .error / .validation_error`
  - `revalidation.started / .completed` ✨
  - `run.completed`

---

## 프로젝트 구조

```
aiworld-harness/
├── README.md
├── run.sh
├── requirements.txt
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py                        # FastAPI entry · REST · WebSocket · static
│   ├── config.py                      # env · CROSS_MATRIX
│   ├── db.py                          # SQLite 스키마 · init_db()
│   ├── orchestrator.py                # 파이프라인 제어 · 재생성 루프 · revalidate_run()
│   ├── ws.py                          # WebSocket 매니저
│   ├── prompts_store.py               # 프롬프트 override resolve
│   ├── agents/
│   │   ├── base.py                    # Claude/OpenAI 통합 LLM 클라이언트
│   │   ├── course_planner.py
│   │   ├── figure_rationale.py
│   │   ├── story_writer.py            ✨
│   │   ├── material_writer.py
│   │   ├── quiz_generator.py
│   │   ├── special_quiz_generator.py  ✨
│   │   └── practice_generator.py
│   ├── validators/
│   │   ├── schema_validator.py        # 코드 자동 규칙
│   │   ├── rubric_validator.py        # LLM-as-judge
│   │   └── glossary_validator.py      ✨ 표준 용어 검증
│   └── exporters/
│       ├── xlsx_export.py             # openpyxl
│       ├── sql_export.py              ✨ INSERT SQL 생성
│       ├── html_export.py             ✨ 학습자료 HTML
│       ├── docx_export.py             # python-docx
│       └── zip_export.py              # xlsx + docx 번들
│
├── frontend/
│   └── index.html                     # 단일 파일 SPA · 다크/라이트 모드 ✨
│
├── data/
│   ├── aiworld.db                     # SQLite (gitignore)
│   ├── schema-v1.json
│   ├── rubric-v1.yaml
│   ├── glossary.yaml                  ✨ 표준 용어 사전
│   └── goldens/
│
├── design-library/
│   └── ...                            # 재사용 가능 UX/UI 자산
│
└── scripts/
    ├── push-to-github.sh
    └── auto-pull-watcher.sh
```

---

## Export

### xlsx (주 산출물)
`GET /api/runs/{id}/export.xlsx` 또는 UI 배포 탭
- 설정 / 개요 / 커리큘럼 / 위인 선정 배경 / 퀴즈 / 실습 / 학습자료 요약

### SQL ✨
`GET /api/runs/{id}/export.sql` 또는 UI 배포 탭
- `quiz` 테이블 INSERT — OX/단일/복수/분류/단답형 포맷 자동 변환
- `practice` 테이블 INSERT — criteria JSON 포함
- `course_practice_quiz` 테이블 INSERT — 순서·COURSE_ID·CLIP_GROUP_ID placeholder
- ID는 placeholder 시작값(`QUIZ_ID_START=900001`)으로 생성, 개발팀이 실제 값으로 교체 후 실행

### docx (학습자료)
- **개별**: Review에서 material 컴포넌트 → 헤더 `.docx` 버튼
- **번들**: `GET /api/runs/{id}/export.zip`

---

## 재생성 루프

### 3가지 Scope
| Scope | 트리거 | 컨텍스트 상속 |
|---|---|---|
| **item** | 플래그 카드 "재생성" 버튼 | 기획서 + 형제 항목 + 수정 지시 |
| **chapter** | 프리뷰 헤더 "이 챕터 전체 재생성" | 기획서 + 이전 버전 + 피드백 |
| **revalidate** ✨ | Review 탭 "검증 재실행" 버튼 | 현재 generated/validation_error 전체 |

### 종료 조건
- ✅ 재검증 통과 → 새 버전 approved
- ⚠️ 재시도 상한(기본 3회) 도달 → BORDERLINE 격상
- ↩️ 사용자 "무시하고 통과" → 즉시 종료

---

## Admin 페이지

사이드바 **환경설정** 탭:

1. **환경 설정** — 모델명·API 키 마스킹·재시도 상한·합격선·서버 주소
2. **API 키 변경** ✨ — Anthropic/OpenAI 키 UI 입력 → `.env` 자동 저장 → 서버 재시작
3. **교차검증 매트릭스** — 컴포넌트 × 생성자/검증자 테이블
4. **에이전트 시스템 프롬프트** — 아코디언 편집 (저장/재설정/복사)

---

## Design Library

`design-library/` 폴더는 다른 자동화 프로덕트에 재사용 가능한 UX/UI 자산.

**새 자동화 프로젝트 시작 시**:
1. `design-library/principles.md` 8원칙 점검
2. `00-foundation/tokens.json` import
3. `02-patterns/` 중 필요한 패턴 채택
4. `instances/_template/` 복사해 프로젝트 고유 문서 생성

---

## Contributing

```bash
git checkout -b feature/my-change
# 변경 후
./run.sh  # 브라우저 확인
git commit -m "[feat] 설명"
git push origin feature/my-change
# GitHub에서 v2.0 브랜치로 PR
```

### 커밋 타입
`feat` · `fix` · `refactor` · `docs` · `chore`

### 주의
- `.env` 절대 커밋 금지
- `data/aiworld.db` 로컬 전용, 공유 금지
- Admin 프롬프트 override도 로컬 DB 전용

---

## 보안 주의

- `.env`는 `.gitignore` 포함. 절대 커밋 금지.
- 이 저장소는 **Private**
- 내부망 배포 수준의 인증은 MVP 비포함. 외부 공유 시 reverse proxy + basic auth 필수.

---

## 로드맵

- ✅ 파이프라인 전체 (7개 컴포넌트 타입 × 교차검증)
- ✅ 5-Tab UX · 3-pane Review · 재생성 루프
- ✅ 배포 탭 — xlsx + SQL export
- ✅ 검증 재실행 (일괄 revalidate)
- ✅ Admin API 키 UI 편집
- ✅ 다크 / 라이트 모드 전환
- ✅ 플래그 6종 (GLOSSARY 추가)
- ✅ glossary_validator · story_writer · special_quiz_generator
- 🔨 PoC 1과정으로 루브릭·프롬프트 재튜닝
- 🔨 SQL ID placeholder 자동화 (개발팀 DB 연동)

---

## 라이선스 · 크레딧

내부 사용 목적으로 작성됨. 외부 배포·상용화 시 라이선스 별도 합의.

---

*v2.0 · 2026-05-19*

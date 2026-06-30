# AI World Harness — 설계서 v1.0

> 위인 멘토링 시뮬레이션 기반 AI 교육 코스 자동 생성 시스템 (멀티모델 교차검증 + 로컬 서버 + SQL)
>
> 기존 `aiworld-main` (Claude Code 스킬 파이프라인)의 서식·기획 로직을 계승하여, 멀티모델 교차검증·로컬 SQL 관리·Web UI·사내 LAN 배포를 더한 v2 시스템.
>
> 학습자료 `material.html` 화면 렌더링과 PDF 인쇄 품질은 [`design-library/instances/aiworld-harness/material-pdf-design-spec.md`](../design-library/instances/aiworld-harness/material-pdf-design-spec.md)를 메인 디자인 스펙으로 따른다.

---

## 1. 목적과 설계 원칙

- **교차검증 First.** Claude Opus 4.7가 생성하면 GPT-5.4가 검증, 그 반대도 병행. 같은 모델 self-review가 만드는 블라인드 스팟을 제거.
- **플래그 기반 사람 개입.** 사람이 전수 리뷰하지 않는다. 시스템이 "FACT/SCHEMA/BORDERLINE/SENSITIVE/CONSISTENCY" 5종 플래그로 검토 필요 항목을 **위치·사유·체크 가이드와 함께** 큐잉하고, 검토자는 카드만 돌면 된다.
- **항목 단위 재생성.** 재생성 최소 단위는 "항목 1개"(퀴즈 1문제, 실습 1문제, 학습자료 1섹션). 상위 컨텍스트(기획서·프리셋·동일 챕터의 주변 항목)를 그대로 상속해서 전체가 다시 돌지 않게 함.
- **서식은 기존 AI World(콜롬버스 BestPractice)를 그대로 상속.** 결과값 조절(믹서 UI) 파라미터도 기존 서식 범위 안에서만 움직임.
- **한 번 정한 프리셋은 관리자 페이지에서만 수정.** 매 run마다 바꾸지 않음.

---

## 2. 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│ Web UI (React + Tailwind, via FastAPI static serving)    │
│ ┌────────────┬──────────────────┬───────────────────────┐│
│ │ Screen 1   │ Screen 2         │ Screen 3              ││
│ │ Control    │ Live Execution   │ Review Dashboard       ││
│ │ Panel      │ (WebSocket)      │ (Flags + Regenerate)   ││
│ └────────────┴──────────────────┴───────────────────────┘│
└────────────────────────┬─────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────┴─────────────────────────────────┐
│ FastAPI Backend (Python 3.11+)                           │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Orchestrator (Director Agent)                        │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌────────────────────┐  ┌─────────────────────────────┐ │
│ │ Generator Agents   │  │ Validator Agents            │ │
│ │ - course-planner   │  │ - schema-validator (코드)   │ │
│ │ - material-writer  │  │ - rubric-validator (LLM)    │ │
│ │ - quiz-generator   │  │ - consistency-validator     │ │
│ │ - practice-gen     │  │                             │ │
│ │ - part-intro       │  │ 교차배치 (Claude↔GPT)       │ │
│ └────────────────────┘  └─────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ SQLite DB (./data/aiworld.db)                        │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                         │
                 Claude API (Opus 4.7) / OpenAI API (GPT-5.4)
```

---

## 3. 3-Screen UX 명세

### Screen 1 · Control Panel (자판기/믹서 UI)

**상단 — 매 run마다 새로 입력**
- 학습 대상 (텍스트 자유입력; 예: "영어학원비 월 30만원 내는 30대 직장인")
- 위인 (텍스트 자유입력)
- 주제 (텍스트 자유입력)
- 학습 목표 3~5개 (태그 형태)
- 과정 분량 (드롭다운: 5P×2 = 10챕터 고정, 추후 확장 가능)

**중단 — 결과값 조절 슬라이더 (기본값은 기존 AI World 서식 기준 자동 세팅)**
- 난이도 분포 (하/중하/중/중상/상 = 2/1/3/2/2, 퀴즈 기준)
- 실습 개수 (3, 기본값) · 퀴즈 개수 (10, 기본값)
- 프롬프트 예시 서식 (good/better 2단 기본, 3단 옵션)
- 힌트 상세도 (간략/표준/상세)
- 스토리 톤 (현실/서사/교훈)
- 위인 활용 강도 (낮음/중간/높음 — 높음은 위인 화법·에피소드 비중↑)
- 검증 엄격도 (fast/standard/strict)
- 타깃 AI 도구 (ChatGPT 고정, 내부용이면 추후 확장)

**하단 — 고정 프리셋 (읽기전용, 관리자 페이지에서만 수정)**
- 서식 버전: `v1.0 (aiworld-main 상속)`
- 톤앤매너 프리셋: `위인 멘토링 시뮬레이션`
- courseId 생성 규칙: `AW-YYYYMMDD-{seq}`
- 루브릭 버전: `rubric-v1.yaml`
- 플래그 타입 정의: `flags-v1.yaml`

**액션**
- `Generate Course Blueprint` 버튼 → Screen 2로 전환

### Screen 2 · Live Execution View

WebSocket으로 실시간 이벤트 푸시.

**레이아웃**
- 상단: Director 기획 단계 진행 상태 (대기 / 생성 중 / 사람 승인 대기 / 승인 완료)
- 중단: 컴포넌트 에이전트 카드 그리드 (학습자료·퀴즈·실습·위인 선정 배경 각각), 각 카드에:
  - 생성자 모델 (Claude / GPT)
  - 검증자 모델 (반대 모델)
  - 현재 상태 (대기 / 생성 / 검증 / 재생성 N회차 / 완료)
  - 교차검증 화살표 시각화
- 하단: 실시간 이벤트 로그 스트림
  - `[16:23] quiz-1-1 생성 시작 (Claude)`
  - `[16:24] quiz-1-1 생성 완료 → 검증 시작 (GPT)`
  - `[16:25] quiz-1-1 [중] 복수선택 정답 개수 오류 → 재생성 지시`
  - `[16:26] quiz-1-1 재생성 v2 완료 → 검증 통과`

**중단 게이트**
- Director가 과정 기획서 생성 완료 시 **사용자 승인** 필수 (기존 aiworld-orchestrator 룰 계승)
- 승인 이후 컴포넌트 병렬 생성 개시

### Screen 3 · Review Dashboard

**레이아웃**
- 좌측 Sidebar: 필터
  - 플래그 타입별 (FACT / SCHEMA / BORDERLINE / SENSITIVE / CONSISTENCY) — 배지 수 표시
  - 컴포넌트별 (학습자료 / 퀴즈 / 실습 / 위인 선정 배경)
  - 챕터별 (1-1 ~ 5-2)
  - 상태 (미해결 / 해결 / 보류)
- 중앙 Main: 플래그 카드 리스트 (기본: 심각도·챕터 순 정렬)
  - 카드 헤더: `[FACT] 2-1 실습 2 정답` + 해결/보류 버튼
  - 카드 본문:
    - **사유**: "위인 어록 인용이 출처 미확인"
    - **위치**: `실습 탭 > 2-1 > J열 (정답)`
    - **체크 가이드**: "원 출처 확인. 미상이면 '전해지는 말' 표기 또는 삭제"
    - **원문 (읽기전용)**: 해당 항목의 생성된 전체 내용
    - **수정 지시 입력창** (자유 텍스트)
    - **[재생성] 버튼** / **[인라인 편집]** 토글 / **[무시하고 통과]**
- 우측 Summary
  - 전체 진척도 (미해결 N / 해결 M / 전체 P)
  - `[모든 해결 항목 배포]` — 최종 승인
  - `[CSV/XLSX로 내보내기]`

---

## 4. 데이터 모델 (SQLite)

```sql
-- 사용자 입력 1회 = run 1개
CREATE TABLE runs (
  run_id        TEXT PRIMARY KEY,       -- AW-20260422-001
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status        TEXT,                   -- planning | approved | generating | reviewing | deployed | aborted
  inputs_json   TEXT,                   -- Screen 1의 전체 입력값
  mixer_json    TEXT,                   -- Screen 1의 믹서 슬라이더 값
  preset_version TEXT                   -- 사용한 프리셋 스냅샷 버전
);

-- 과정 기획서 (Director 결과물)
CREATE TABLE blueprints (
  blueprint_id  TEXT PRIMARY KEY,
  run_id        TEXT REFERENCES runs(run_id),
  version       INTEGER DEFAULT 1,
  content_json  TEXT,                   -- 코스명, 개요, 커리큘럼 10챕터 전체
  generator_model TEXT,                 -- claude-opus-4-7 | gpt-5.4
  approved_at   TIMESTAMP
);

-- 컴포넌트 (학습자료·퀴즈·실습·파트인트로의 개별 산출물 단위)
-- 퀴즈는 1 챕터 = 10문항 단위, 실습은 1 챕터 = 3문제 단위, 학습자료는 1 챕터 = 1 doc
CREATE TABLE components (
  component_id   TEXT PRIMARY KEY,      -- quiz-1-1-v1 / practice-1-1-v2
  run_id         TEXT REFERENCES runs(run_id),
  blueprint_id   TEXT REFERENCES blueprints(blueprint_id),
  type           TEXT,                  -- course_overview | figure_rationale | curriculum | material | quiz | practice
  chapter_id     TEXT,                  -- 1-1 (해당 없으면 null)
  version        INTEGER DEFAULT 1,
  generator_model TEXT,
  validator_model TEXT,
  content_json   TEXT,                  -- 컴포넌트 본문 (스키마 v1.0 준수)
  status         TEXT,                  -- generated | validating | passed | flagged | regenerating | approved
  parent_version INTEGER,               -- 재생성 시 어느 버전에서 파생됐나
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 검증 기록 (루브릭 항목별 판정)
CREATE TABLE validations (
  validation_id   TEXT PRIMARY KEY,
  component_id    TEXT REFERENCES components(component_id),
  validator_type  TEXT,                 -- schema | rubric | consistency
  validator_model TEXT,                 -- claude | gpt (code validator인 경우 null)
  rubric_results_json TEXT,             -- 항목별 상/중/하 판정 + 점수 + 증거
  overall_score   REAL,
  passed          BOOLEAN,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 플래그 (사람 검토 대상)
CREATE TABLE flags (
  flag_id       TEXT PRIMARY KEY,
  component_id  TEXT REFERENCES components(component_id),
  run_id        TEXT REFERENCES runs(run_id),
  flag_type     TEXT,                   -- FACT | SCHEMA | BORDERLINE | SENSITIVE | CONSISTENCY
  severity      TEXT,                   -- 상 | 중 | 하
  location_path TEXT,                   -- "실습 탭 > 2-1 > J열 (정답)"
  reason        TEXT,
  guide         TEXT,                   -- 체크 가이드 (사람이 어떻게 확인할지)
  origin_text   TEXT,                   -- 플래그된 원문
  resolved      BOOLEAN DEFAULT 0,
  resolution    TEXT,                   -- regenerated_v2 | inline_edited | dismissed | approved
  resolved_at   TIMESTAMP
);

-- 재생성 이력 (어떤 수정 지시로 어느 버전이 만들어졌나)
CREATE TABLE regenerations (
  regen_id          TEXT PRIMARY KEY,
  source_component_id TEXT REFERENCES components(component_id),
  target_component_id TEXT REFERENCES components(component_id),
  flag_id           TEXT REFERENCES flags(flag_id),  -- nullable
  scope             TEXT,                -- item | chapter | component
  user_instruction  TEXT,                -- 사용자가 입력한 수정 지시
  generator_model   TEXT,
  validator_model   TEXT,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 프리셋 (서식 / 루브릭 / 키워드 등)
CREATE TABLE presets (
  preset_key     TEXT PRIMARY KEY,      -- schema_v1 | rubric_v1 | flags_v1 | tone_v1 | courseid_rule_v1
  version        TEXT,
  value_json     TEXT,
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 골드 스탠다드 few-shot 저장소
CREATE TABLE goldens (
  golden_id   TEXT PRIMARY KEY,
  type        TEXT,                     -- quiz | practice | material | course_overview
  label       TEXT,                     -- "한석봉 1-1 퀴즈 단답형"
  content_json TEXT,
  source_run  TEXT                      -- 어느 과정에서 추출했는지
);
```

---

## 5. 재생성 (Regeneration) 프로세스 — 시작·끝 지점 정의

### 5.1 재생성 "시작 지점" 3종 (scope)

| Scope | 트리거 | 상속되는 컨텍스트 | 영향 범위 |
|---|---|---|---|
| **item** | 플래그 카드의 [재생성] 버튼 (가장 빈번) | 기획서 + 챕터 인트로 + 동일 챕터의 다른 항목들(형제) + 프리셋 + **사용자 수정 지시** | 해당 항목 1개만 새 버전 생성 |
| **chapter** | 챕터 단위 '전체 재생성' 버튼 | 기획서 + 프리셋 + 챕터 의도 | 해당 챕터의 학습자료/퀴즈/실습 전체 재생성 |
| **component** | 컴포넌트 전체 재생성 (예: 퀴즈 전체) | 기획서 + 프리셋 | 10챕터의 해당 컴포넌트 전체 재생성 |

기본은 **item scope**. 다른 두 scope는 대규모 서식 오류 발견 시에만 사용.

### 5.2 재생성 "끝 지점"

- **정상 종료**: 재생성된 새 버전이 재검증(schema + rubric + consistency)을 통과 → 플래그 `resolved = true`로 처리 → 새 버전이 `approved` 상태로 DB에 기록
- **재시도 루프 상한 초과**: 기본 3회 재생성해도 통과 못하면 플래그를 `BORDERLINE`으로 격상하고 사람 인라인 편집 요구
- **사용자 수동 종료**: [인라인 편집] 또는 [무시하고 통과] 선택 시 즉시 종료 → DB에 최종 확정 버전 기록

### 5.3 재생성 시 컨텍스트 전달 원칙 (hallucination 방지)

재생성 에이전트에게 반드시 함께 전달:
1. 기획서(blueprint) — 해당 챕터의 파트/챕터명/프롬프트 기법/학습목표
2. 원 항목의 직전 버전 전체 (뭘 바꿔야 하는지 알게)
3. 해당 챕터의 다른 항목들 요약 (consistency 유지)
4. 사용자 수정 지시
5. 프리셋(루브릭·서식)
6. 왜 플래그됐는지 (flag의 reason + guide)

재생성 모델은 **원 생성자와 동일 모델**. 검증자는 **반대 모델**. 교차검증 쌍을 유지함으로써 같은 실수가 다시 통과하지 않도록.

---

## 6. 교차검증 매트릭스

| 컴포넌트 | 1차 생성자 | 1차 검증자 | 비고 |
|---|---|---|---|
| 코스 기획 (overview + curriculum) | Claude Opus 4.7 | GPT-5.4 | 긴 문맥 이해력 우위 → Claude |
| 위인 선정 배경 | GPT-5.4 | Claude Opus 4.7 | |
| 학습자료 (chapter doc) | Claude Opus 4.7 | GPT-5.4 | 깊이·개념설명 |
| 퀴즈 (chapter set) | GPT-5.4 | Claude Opus 4.7 | 서식 안정성 |
| 실습 (chapter set) | Claude Opus 4.7 | GPT-5.4 | 프롬프트 예시 풍부함 |

※ PoC 3~5회 돌려본 결과에 따라 생성/검증 매트릭스를 재튜닝 (관리자 페이지에서 조정 가능).

검증 3단계:
1. **Schema Validator (code)** — JSON schema + quiz-types 규칙 검사. LLM 사용 안함. 통과하지 못한 항목은 **즉시 재생성** (이 단계에서는 사람 개입 없음).
2. **Rubric Validator (LLM-as-judge)** — 루브릭 항목별 상/중/하 판정. 점수 합산이 threshold 미달이면 재생성.
3. **Consistency Validator (code + LLM hybrid)** — 분류 퀴즈 보기 번호 누락·중복, 난이도 순서, 챕터 간 중복, 기획서와의 일치성 검사.

---

## 7. 플래그 5종 정의

| 타입 | 발생 조건 | 체크 가이드 템플릿 |
|---|---|---|
| FACT | 위인 어록·역사적 일화·통계·법령 등 팩트 의심 내용 | "원 출처 확인. 미상이면 '전해지는 말' 또는 삭제" |
| SCHEMA | Schema validator 3회 재시도 후에도 서식 오류 잔존 | "해당 필드의 스키마 v1 규칙 확인 — 수동 편집 또는 서식 변경" |
| BORDERLINE | Rubric validator 점수가 통과선 ±5점 | "루브릭 [항목X]가 중 판정. 상/중 경계 재확인" |
| SENSITIVE | 특정 직군/세대/국적/성별 일반화, 정치·종교적 함의 가능 | "민감 표현 점검. 중립 표현으로 대체 검토" |
| CONSISTENCY | 기획서 vs 컴포넌트, 또는 챕터 간 논리 모순 | "기획서의 학습목표 X와 실습 Y의 불일치. 한쪽 수정 필요" |

**모든 플래그는 반드시 3요소 보유**: 위치(location_path) / 사유(reason) / 체크 가이드(guide)

---

## 8. 루브릭 (rubric-v1.yaml) — 피드백 반영

주신 진규님·재정님 피드백을 그대로 루브릭 항목으로 환원:

**실습 루브릭 (practice)**
- `practice.problem.has_concrete_context` [상] — 문제에 구체 예시/맥락 포함 (단일 키워드 금지)
- `practice.answer.format_is_prompt_example` [상] — 정답이 프롬프트 good/better 형태
- `practice.hint.includes_concrete_example` [상] — 힌트에 프롬프트 작성용 예시 정보
- `practice.difficulty.low_passing_score_tolerant` [중] — 하 난이도 합격컷 0~30점
- `practice.table.schema_strict` [상] — 스키마 v1 준수

**학습자료 루브릭 (material)**
- `material.category.concept_explanation_present` [상] — 카테고리별 전문 개념 설명
- `material.templates.situation_specific_present` [상] — 상황별 복붙 템플릿
- `material.opener.empathy_line_present` [중] — "이런 적 있지 않나요" 공감 오프너
- `material.examples.concrete_and_practical` [상]

**퀴즈 루브릭 (quiz)**
- `quiz.table.schema_strict` [상]
- `quiz.short_answer.format_stable` [중] — 단답형 정답 서식 안정성
- `quiz.distribution.difficulty_balanced` [중]

(전체 루브릭은 `data/rubric-v1.yaml` 참조)

---

## 9. API 명세 (FastAPI REST + WebSocket)

### REST
- `POST /api/runs` — 새 run 시작 (Screen 1 입력값)
- `GET /api/runs/{run_id}` — run 상태 및 구성요소 조회
- `POST /api/runs/{run_id}/approve-blueprint` — Director 기획서 승인
- `GET /api/runs/{run_id}/flags?type=FACT&status=unresolved`
- `POST /api/components/{component_id}/regenerate` — 항목 재생성 (scope, instruction)
- `POST /api/flags/{flag_id}/resolve` — 플래그 해결 (inline_edit / dismiss)
- `GET /api/presets/{preset_key}` / `PUT` (관리자)
- `GET /api/runs/{run_id}/export.xlsx` — 완성본 Excel로

### WebSocket
- `WS /ws/runs/{run_id}` — Screen 2 실시간 이벤트 스트림
  - event types: `blueprint.started`, `blueprint.completed`, `component.generated`, `component.validated`, `component.flagged`, `component.regenerating`, `component.approved`, `run.completed`

---

## 10. 프로젝트 구조

```
aiworld_harness/
├── backend/
│   ├── main.py                  # FastAPI entrypoint + static serving
│   ├── config.py                # env loading (API keys, paths, models)
│   ├── db.py                    # SQLite schema + init
│   ├── orchestrator.py          # Director agent + 파이프라인 제어
│   ├── agents/
│   │   ├── base.py              # LLM client wrapper (Claude + GPT)
│   │   ├── course_planner.py
│   │   ├── material_writer.py
│   │   ├── quiz_generator.py
│   │   ├── practice_generator.py
│   │   └── figure_rationale_writer.py
│   ├── validators/
│   │   ├── schema_validator.py  # 순수 Python validator
│   │   ├── rubric_validator.py  # LLM-as-judge
│   │   └── consistency_validator.py
│   ├── schemas/
│   │   ├── component_schema.json     # 본 문서 9장 기준
│   │   └── rubric_v1.yaml
│   ├── presets.py               # 프리셋 로드/저장
│   └── ws.py                    # WebSocket manager
├── frontend/
│   ├── index.html               # SPA shell
│   ├── app.js                   # React / or vanilla (Phase 1: vanilla)
│   └── style.css                # Tailwind via CDN
├── data/
│   ├── aiworld.db               # SQLite DB
│   ├── schema-v1.json
│   ├── rubric-v1.yaml
│   └── goldens/
│       └── columbus/            # 기존 BestPractice few-shot
├── docs/
│   └── DESIGN.md                # 본 문서
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 11. 배포 (로컬 + 사내 Wi-Fi)

**개발/실행**
```bash
# 1. 환경 세팅
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. DB 초기화 (1회)
python backend/db.py init

# 3. .env 생성 (.env.example 복사 후 API 키 입력)
cp .env.example .env

# 4. 서버 기동
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 접속
#   이 PC:          http://localhost:8000
#   사내 Wi-Fi 내:  http://{이 PC의 내부 IP}:8000
```

**내부 IP 확인 (macOS)**
```bash
ipconfig getifaddr en0    # 유선 / Wi-Fi 기본
# 또는 ifconfig | grep "inet " | grep -v 127.0.0.1
```

**방화벽 허용 (macOS)**: 시스템 설정 → 네트워크 → 방화벽 → 앱별 허용 목록에 `python` / `uvicorn` 추가. 1회 설정.

**보안 주의**
- `.env`는 `.gitignore`에 포함되어 있음. API 키는 절대 커밋 금지.
- 내부망 배포 수준의 인증은 MVP에 포함하지 않음. 외부 접근 필요 시 reverse proxy + basic auth 추가 필요.
- 이 설계서 작성 과정에서 채팅으로 전달받은 API 키는 **반드시 로테이트 권장** (OpenAI/Anthropic 콘솔에서 재발급).

---

## 12. Phase 로드맵

| Phase | 산출물 | 기간 |
|---|---|---|
| **Phase 0 (지금)** | 설계서·스키마·루브릭·프로젝트 스캐폴드 | 1일 |
| **Phase 1 MVP** | Director + 퀴즈·실습 에이전트 1세트 + Schema Validator + 최소 UI (Screen 1 & Screen 3) | 1주 |
| **Phase 2** | 교차검증 매트릭스 전 컴포넌트 적용 + Rubric Validator (LLM-judge) + Screen 2 실시간 뷰 | 1주 |
| **Phase 3** | 재생성 루프 완성 + 플래그 해결 UI + xlsx export | 3일 |
| **Phase 4** | PoC 1과정 돌려서 루브릭/프롬프트/모델 매트릭스 재튜닝 | 1주 |

---

*v1.0 — 2026-04-22*

# AI World Harness

"위인 멘토링 시뮬레이션" 콘셉트의 AI 프롬프트 교육 코스를 자동 생성하는 시스템.

---

## 프로젝트 개요

- **목적**: 기획자 입력(위인 + 주제 + 학습 대상) → 10챕터 교육 코스(학습자료·퀴즈·실습) 자동 생성 + 교차검증
- **도메인**: 콘텐츠 자동 생성 (교육 콘텐츠)
- **스택**: FastAPI + SQLite + Tailwind CDN + Pretendard + vanilla JS
- **주요 사용자**: 전략기획 팀장·콘텐츠 기획자·검토자

---

## 채택한 공통 패턴

- [x] Tier 입력 레이아웃 (Tier 1 / 2 / 프리셋)
- [x] 3-Screen 플로우 (Control / Execution / Review)
- [x] 교차검증 UI (Claude ↔ GPT)
- [x] 에이전트 상태 Kanban
- [x] 플래그·앵커 시스템 (FACT/SCHEMA/BORDERLINE/SENSITIVE/CONSISTENCY)
- [x] 항목·챕터 단위 재생성 (피드백 주입)
- [x] WebSocket 실시간 진행
- [x] 편집 가능한 기획서 검토

---

## 이 프로젝트 고유 요소

- **콘텐츠 타입 5종**: course_overview / figure_rationale / material / quiz / practice
- **도메인 톤**: "위인 멘토링 시뮬레이션" — 학습자는 위인의 제자, 위인이 직접 가르침
- **메인 학습자료 디자인 스펙**: [`material-pdf-design-spec.md`](./material-pdf-design-spec.md) — `material.html` 화면 렌더링과 PDF 인쇄 품질의 기준 문서
- **루브릭 56항목** (`data/rubric-v1.yaml`)
- **스키마 7개 정의** (`data/schema-v1.json`)
- **교차검증 매트릭스**: 컴포넌트별 Claude/GPT 배분 (`backend/config.py`)

---

## 파일

- [flag-types-5.md](./flag-types-5.md) — 5종 플래그 정의
- [rubric-label-dictionary.md](./rubric-label-dictionary.md) — 루브릭 id → 한글
- [domain-tone-guide.md](./domain-tone-guide.md) — 위인 멘토링 톤
- [component-types.md](./component-types.md) — 5개 컴포넌트 타입
- [material-pdf-design-spec.md](./material-pdf-design-spec.md) — 학습자료 HTML/PDF 메인 디자인 스펙

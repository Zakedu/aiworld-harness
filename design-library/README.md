# Design Library — 자동화 프로덕트 UX/UI 자산

> AI World Harness를 만들며 추출한 **재사용 가능한 UX/UI 규칙·컴포넌트·패턴 집합**.
> 앞으로 다른 자동화 프로덕트(문서 자동 생성, 마케팅 카피 자동화, 법률 검토 자동화 등)를 시작할 때 참조·복사해서 쓰는 것이 목적.

---

## 사용법

1. **새 자동화 프로젝트를 시작한다면**
   1. [`principles.md`](./principles.md)를 먼저 읽어 8개 원칙 점검
   2. [`00-foundation/tokens.json`](./00-foundation/tokens.json) 을 프론트엔드 CSS 변수/Tailwind config로 임포트
   3. [`02-patterns/`](./02-patterns/)에서 필요한 패턴만 선택 (전체 8개 중 이 프로젝트에 해당하는 것만)
   4. [`instances/_template/`](./instances/_template/)을 복사해 프로젝트 고유 사항 기록 시작

2. **컴포넌트가 필요하다면** → [`01-components/component-catalog.md`](./01-components/component-catalog.md)에서 원자·분자·유기체 목록 확인

3. **특정 화면을 만들고 있다면** → [`03-screens-reference.md`](./03-screens-reference.md) 3-Screen 템플릿 참고

4. **사람 검토 루프를 설계하고 있다면** → [`02-patterns/flag-anchor-system.md`](./02-patterns/flag-anchor-system.md), [`02-patterns/item-and-batch-regeneration.md`](./02-patterns/item-and-batch-regeneration.md)

5. **AI World Harness 학습자료 HTML/PDF 디자인을 수정한다면** → [`instances/aiworld-harness/material-pdf-design-spec.md`](./instances/aiworld-harness/material-pdf-design-spec.md)를 메인 스펙으로 따른다.

---

## 폴더 구조

```
design-library/
├── README.md                         ← 현재 문서
├── principles.md                     ← 자동화 UX 핵심 원칙 8개
├── 00-foundation/
│   ├── tokens.json                   ← Color / Type / Spacing 토큰 (코드 import용)
│   └── tokens.md                     ← tokens.json 설명과 사용 예시
├── 01-components/
│   └── component-catalog.md          ← 원자·분자·유기체 카탈로그
├── 02-patterns/                      ← 자동화 공통 인터랙션 패턴
│   ├── cross-validation-ui.md
│   ├── agent-status-kanban.md
│   ├── flag-anchor-system.md
│   ├── item-and-batch-regeneration.md
│   ├── editable-blueprint-review.md
│   ├── websocket-live-progress.md
│   ├── three-screen-flow.md
│   └── tiered-input-layout.md
├── 03-screens-reference.md           ← Control / Execution / Review 3-Screen 템플릿
├── 04-flows-reference.md             ← 주요 유저 플로우 다이어그램
├── 05-state-matrix.md                ← 컴포넌트별 상태 표
├── 06-content-voice.md               ← UX 카피 원칙 + 한글 라벨 규칙
├── 07-a11y-and-specs.md              ← 접근성 / 반응형 / 애니메이션
├── 08-governance.md                  ← 라이브러리 유지·기여 프로세스
└── instances/
    ├── _template/                    ← 새 프로젝트 시작 시 복사본
    └── aiworld-harness/              ← 이 프로젝트 고유 자산
        ├── README.md
        ├── flag-types-5.md
        ├── rubric-label-dictionary.md
        ├── domain-tone-guide.md
        ├── component-types.md
        └── material-pdf-design-spec.md ← 학습자료 HTML/PDF 메인 디자인 스펙
```

---

## 원본 프로덕트

이 라이브러리는 **AI World Harness** (`/Users/ga/Projects/aiworld_harness`)를 구축하며 추출됨.
- 스택: FastAPI + SQLite + Tailwind CDN + Pretendard + vanilla JS
- 도메인: "위인 멘토링 시뮬레이션" 기반 AI 프롬프트 교육 코스 자동 생성
- 멀티모델 교차검증 (Claude Opus 4.7 ↔ GPT-5.4)

이 라이브러리의 대부분 토큰·패턴은 **스택 중립**이라 React/Vue/Svelte/모바일 네이티브에도 같은 원칙으로 적용 가능.

---

## 버전

- **v1.0 · 2026-04-22** — 초기 추출
- 작성자: Jake (전략기획 팀장) + Claude

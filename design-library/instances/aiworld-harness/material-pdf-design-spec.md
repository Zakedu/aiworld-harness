# AI World 학습자료 PDF 디자인 스펙 가이드

> 학습자료(`material.html`) 화면 렌더링 + PDF 인쇄 품질을 일관되게 유지하기 위한 디자인 규칙.
> 신규 챕터 추가·기존 챕터 재생성·새 컴포넌트 도입 시 이 문서의 원칙을 따른다.
>
> **적용 위치**: `backend/exporters/html_export.py` 내 `_CSS` 블록
> **최종 갱신**: 2026-05-29

---

## 1. 디자인 원칙

1. **타이포그래피 중심** — 이모지·장식·도형 의존 없이 활자 위계로만 정보를 구조화한다.
2. **라이트 톤 일관** — 화면이든 인쇄든 흰 바탕 + 짙은 글씨가 기본. 컬러는 라벨·구분 액센트로만 사용.
3. **인쇄(PDF) 우선** — 학습자료는 출력·배포되는 문서다. 화면에서만 멋있고 인쇄에서 무너지면 실패.
4. **고아 금지** — 제목만 한 페이지에 남고 본문이 다음 장으로 밀리는 패턴은 절대 허용하지 않는다.

---

## 2. 타이포그래피 스펙

| 요소 | 화면 | 인쇄 | 폰트 |
|---|---|---|---|
| 챕터 타이틀 (`.chapter-title`) | 28px / 700 | 28px | Noto Serif KR |
| 섹션 헤딩 (`.section-heading`) | 17px / 600 | 16px | Noto Serif KR |
| 본문 (`body`) | **15px** / 400 | **14px** | Noto Sans KR |
| 사전지식 박스 (`.bg-knowledge`) | 14px | 14px | Noto Sans KR |
| BGB 카드 본문 (`.bgb-body`) | 14px | 13.5px | JetBrains Mono |
| 체크리스트 (`.checklist li`) | 14px | 14px | Noto Sans KR |
| 요약 박스 (`.summary-box p`) | 14px | 14px | Noto Sans KR |
| 표 (`.md-body table`) | 14px | 14px | Noto Sans KR |
| 인라인 코드 (`.md-body code`) | 13px | 13px | JetBrains Mono |
| 라벨/메타 (`.section-label`, `.chapter-meta`) | 10~11px / letter-spacing 0.18~0.22em | 동일 | Noto Sans KR |

**원칙**
- 본문 하한선: **14px** (화면) / **13.5px** (인쇄). 그 아래로는 한국어 가독성 급락.
- 한국어는 `word-break: keep-all` 필수 (어절 단위 줄바꿈).
- `line-height: 1.8~1.85` — 한국어 라틴 혼용 줄간격.

---

## 3. 컬러 토큰

```css
--ink:        #1c1c1e;   /* 본문 텍스트 */
--mid:        #48484a;   /* 보조 텍스트, 메타 */
--light:      #f5f5f0;   /* 박스 배경 (베이지) */
--accent:     #1d3557;   /* 강조 (다크 블루) */
--accent-mid: #457b9d;   /* 보조 강조 */
--bad:        #7c2d12;   /* 실패/주의 */
--good:       #14532d;   /* 성공/권장 */
--better:     #1e3a5f;   /* 최선/심화 */
--border:     #d1cfc8;   /* 박스 테두리 */
--rule:       #e5e3dc;   /* 가는 구분선 */
--print-bg:   white;     /* 인쇄 배경 (강제 흰색) */
```

**액센트 컬러 사용 규칙**
- 본문 글씨에는 액센트 컬러 X. 본문은 항상 `--ink`.
- BGB 카드 헤더, 섹션 라벨, 토큰 하이라이트에만 사용.

---

## 4. 컴포넌트별 디자인 규칙

### 4.1 섹션 (`.section`)

- 라벨 → 헤딩 → 본문 순서 고정.
- 라벨: 영문 카테고리(예: `CORE CONCEPT`, `PROMPT PRACTICE`, `APPLIED SCENARIOS`, `REVIEW`).
- 헤딩 왼쪽에 3px 짙은 블루 세로 막대(`border-left: 3px solid var(--accent)`).
- 섹션 간 구분선(`<hr class="section-rule">`) — 마지막 섹션 뒤에는 없음.

### 4.2 사전지식 박스 (`.bg-knowledge`)

- 베이지(`--light`) 배경 + 좌측 3px 블루 stripe.
- 작은 라벨("사전 지식") + 본문.
- 단독 페이지에 들어갈 정도의 분량 (한 박스 = 한 토픽).

### 4.3 BAD / GOOD / BETTER 카드 (`.bgb-card`)

**원칙**: 흰 바탕 + 검정 본문 + 헤더에만 컬러 액센트.

| 부분 | 스펙 |
|---|---|
| 카드 배경 | `white` |
| 카드 테두리 | `1px solid var(--border)` |
| 헤더 배경 | BAD `#fdf2f2` / GOOD `#f1f8f3` / BETTER `#f1f4fb` (옅은 톤) |
| 헤더 글씨 | BAD `#b91c1c` / GOOD `#15803d` / BETTER `#1d4ed8` (짙은 톤) |
| 본문 글씨 | `var(--ink)` 14px |
| 본문 폰트 | `JetBrains Mono` (프롬프트 코드 느낌 유지) |

**토큰 하이라이트 (`_tokenize_body`)**
- `프롬프트:` → `.tok-keyword` 짙은 빨강 `#b91c1c` bold
- `"문자열"` → `.tok-string` 짙은 녹색 `#15803d`
- `[변수]` → `.tok-var` 짙은 파랑 `#1d4ed8`
- `**강조**` → `.tok-bold` 짙은 금색 `#a16207` bold

> ⚠️ 다크 모드(검정 배경 + 형광 컬러)는 사용 금지. Chrome PDF 출력 시 배경이 빠져 글씨가 흐려진다.

### 4.4 체크리스트 (`.checklist`)

- 항목당 14px, line-height 1.65.
- 좌측 16px 정사각형 체크박스(흰 바탕 + 1.5px 보더).
- 각 항목 사이 `--rule` 가는 구분선.

### 4.5 요약 박스 (`.summary-box`)

- 옅은 회색 배경(`#fafafa`) + 좌측 4px 다크 stripe.
- 핵심 요약 1~3문장에 사용. 길어지면 일반 본문으로 분리.

### 4.6 표 (`.md-body table`)

- 14px, 헤더 셀 배경 `--light`, 짝수 행 배경 `#fafaf8`.
- 테두리 `--border` 균일.
- `vertical-align: top` — 셀 높이가 달라도 위 정렬.

---

## 5. PDF / 인쇄 출력 규칙 ★

학습자료는 PDF 배포가 1순위 용도. 아래 규칙은 모두 `@media print {}` 블록에 들어간다.

### 5.1 컬러 보존 (필수)

```css
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
```

- 이 한 줄이 빠지면 Chrome의 "Background graphics" 옵션이 꺼졌을 때 모든 박스 배경·헤더 컬러가 사라진다.
- BAD/GOOD/BETTER 헤더의 옅은 컬러 배경이 PDF에 살아남으려면 반드시 필요.

### 5.2 페이지 분할 — 고아 제목(orphan heading) 방지

**문제 패턴**

```
[ 페이지 N ]                   [ 페이지 N+1 ]
─────────────────              ─────────────────
PROMPT PRACTICE                ┌─ BAD ─────────┐
[ 더 좋은 프롬프트 만들기 ]      │ 프롬프트: ... │
                               └───────────────┘
(나머지 페이지 텅 빔)             ┌─ GOOD ────────┐
                                ...
```

→ 제목과 본문 사이에서 페이지가 끊기는 현상. 학습자료에서 가장 자주 발생하는 인쇄 결함.

**원인**
- 어떤 컨테이너에 `page-break-inside: avoid`가 걸려 있는데 그 컨테이너가 한 페이지에 안 들어갈 때, 통째로 다음 장으로 밀리면서 직전 페이지에 헤딩만 남는다.
- 예: `.bgb-grid { page-break-inside: avoid }` — 3장 카드 묶음 전체를 한 페이지에 강제하면, 안 들어가는 순간 카드 묶음이 다음 장으로 가버리고 그 위의 섹션 헤딩만 남는다.

**해결 규칙 (반드시 함께 적용)**

```css
@media print {
  /* (A) 제목/라벨 뒤에서는 페이지 끊기 금지 */
  .section-label      { break-after: avoid; page-break-after: avoid; }
  .section-heading    { break-after: avoid; page-break-after: avoid; }
  .bg-knowledge-label { break-after: avoid; page-break-after: avoid; }
  h1, h2, h3, h4      { break-after: avoid; page-break-after: avoid; }

  /* (B) "한 단위"로 묶여야 하는 것만 break-inside: avoid */
  .bgb-card     { break-inside: avoid; page-break-inside: avoid; }
  .bg-knowledge { break-inside: avoid; page-break-inside: avoid; }
  .summary-box  { break-inside: avoid; page-break-inside: avoid; }
  .checklist li { break-inside: avoid; page-break-inside: avoid; }
  table, tr, thead, tbody { break-inside: avoid; page-break-inside: avoid; }
}
```

**금지 규칙**

```css
/* ❌ 절대 쓰지 말 것 */
.bgb-grid { page-break-inside: avoid; }   /* 카드 묶음 전체를 원자화 → 고아 제목 유발 */
.section  { page-break-inside: avoid; }   /* 섹션 전체를 원자화 → 고아 제목 유발 */
```

→ **"단일 의미 단위"(카드 1장, 표 1행, 체크리스트 1항목)에만 `break-inside: avoid`**를 걸고, 묶음 컨테이너(`.bgb-grid`, `.section`)에는 절대 걸지 않는다.

### 5.3 페이지 마진

```css
@page { margin: 20mm 18mm; }
```

A4 기준 위·아래 20mm / 좌·우 18mm. 챕터 상단 헤더 + 하단 풋터의 여백과 시각적으로 맞춤.

### 5.4 인쇄 시 폰트 약간 축소

- 화면 본문 15px → 인쇄 14px. 너무 축소하면 가독성 손상, 너무 키우면 페이지 수 폭증.
- 섹션 헤딩 17px → 16px. 위계는 유지하되 인쇄 페이지 위계와 맞춤.
- BGB 카드 본문 14px → 13.5px (모노스페이스라 같은 px도 더 빽빽하므로).

### 5.5 인쇄 전용 UI 숨김

```css
.print-bar { display: none !important; }
```

화면용 "닫기 / PDF 저장" 버튼 바는 인쇄에서 반드시 숨김.

---

## 6. 새 컴포넌트 추가 시 체크리스트

신규 박스·카드·리스트 타입을 추가할 때 아래를 확인:

- [ ] 본문 폰트가 14px 이상인가? (인쇄 13.5px 이상)
- [ ] 배경은 흰색 또는 옅은 라이트 톤인가? (다크 배경 금지)
- [ ] 컬러는 라벨·헤더·구분에만 쓰고 본문 글씨는 `--ink`인가?
- [ ] "단일 의미 단위"라면 `@media print`에 `break-inside: avoid` 추가했는가?
- [ ] 묶음 컨테이너에는 `break-inside: avoid`를 **안** 걸었는가?
- [ ] 라벨/헤딩 역할 요소라면 `break-after: avoid` 추가했는가?
- [ ] 옅은 컬러 배경을 쓴다면 `print-color-adjust: exact`가 켜져 있는가? (전역에 켜져 있으면 OK)
- [ ] 한국어 본문에 `word-break: keep-all` 적용되는 경로인가? (`.section-body` 또는 `.md-body` 안이면 OK)
- [ ] 화면에서 잘 보이는지 + Chrome "Print to PDF"로 출력해서도 같은 형태인지 두 번 확인했는가?

---

## 7. 변경 이력

### 2026-05-29 (현재 적용본)
- **라이트 톤 전환**: BGB 카드 다크(`#09090b` 배경 + 형광 토큰) → 라이트(흰 배경 + 짙은 토큰).
- **본문 폰트 +1px**: 14px → 15px (화면), 13px → 14px (인쇄).
- **사전지식/표/체크리스트/요약 통일**: 모두 14px로 정리.
- **인라인 코드**: 12px → 13px.
- **인쇄 색상 보존**: `print-color-adjust: exact` 추가 → BGB 헤더의 옅은 컬러 배경이 PDF에도 살아남음.
- **고아 제목 방지**:
  - `.section-heading` / `.section-label` / `h1~h4` 에 `break-after: avoid` 추가.
  - `.bgb-grid` 와 `.section` 의 `page-break-inside: avoid` **제거** (이게 고아 제목 원인이었음).
  - 단일 단위(`.bgb-card`, `.bg-knowledge`, `.summary-box`, `.checklist li`, `table/tr`)에만 `break-inside: avoid` 유지.

### (이전 버전 — `html_export.py.bak`에 보관)
- 다크 코드 에디터 스타일 BGB 카드, 본문 14px, 묶음 단위 atomic.

---

## 8. 적용 방법

1. `backend/exporters/html_export.py` 의 `_CSS` 블록을 본 가이드의 §2~§5 기준으로 유지.
2. 변경 후 서버는 uvicorn `--reload` 모드라 자동 리로드 → 브라우저 새로고침만 하면 화면 반영.
3. PDF 확인은 반드시 Chrome "인쇄 → PDF로 저장"으로 직접 테스트 (Safari·Preview는 결과 다름).
4. 새 컴포넌트 도입 시 §6 체크리스트를 반드시 통과시킨 후 머지.

---

## 9. 참고 — 라이트 톤 BGB 카드 컬러 매트릭스

| 카드 | 헤더 배경 | 헤더 글씨 | 토큰 컬러 매핑 |
|---|---|---|---|
| BAD | `#fdf2f2` | `#b91c1c` | 프롬프트:=빨강 / "문자열"=녹색 / [변수]=파랑 / **강조**=금색 |
| GOOD | `#f1f8f3` | `#15803d` | (동일) |
| BETTER | `#f1f4fb` | `#1d4ed8` | (동일) |

토큰 컬러는 카드 종류와 무관하게 의미 단위로 고정 (프롬프트=빨, 문자열=녹, 변수=파, 강조=금).

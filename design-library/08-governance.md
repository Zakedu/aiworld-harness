# Governance — 라이브러리 유지·확장 프로세스

---

## 원칙

이 디자인 라이브러리는 **살아있는 문서**다. 실제 프로덕트 빌드를 통해 검증된 것만 추가·수정한다.

---

## 버전 관리

- 루트 `README.md` 하단의 "버전" 섹션에 기록
- 파일별 변경은 git log로 추적
- 의미 있는 변경은 `CHANGELOG.md` 한 줄 (향후 추가)

### 버전 bump 기준
- **major (v2.0)**: 토큰 이름 변경, 원칙 추가/삭제, 패턴 폐기
- **minor (v1.1)**: 새 컴포넌트 추가, 기존 패턴 확장
- **patch (v1.0.1)**: 문서 수정, 오타, 예시 보강

---

## 기여 프로세스

### 새 컴포넌트 추가
1. 실제 프로젝트에서 **최소 1회 검증**됐는가?
2. 기존 원자·분자·유기체 중 재사용 가능한지 먼저 확인
3. 토큰만 사용 (hardcode 금지)
4. 최소 3개 상태 정의
5. `01-components/component-catalog.md`에 한 줄 추가
6. 스크린샷 또는 HTML 스니펫 example (`assets/`에 저장)

### 새 패턴 추가
1. 두 개 이상 프로젝트에서 **반복**되었는가? (1회용은 인스턴스 폴더로)
2. "언제 쓰나 / 왜 / 구조 / anti-패턴 / 관련 원칙" 5섹션 필수
3. `02-patterns/` 하위에 새 `.md` 파일 생성
4. README의 폴더 구조 표에도 업데이트

### 토큰 변경
1. 기존 값을 바꾸는 경우 → 해당 프로젝트 모두 확인 (breaking change)
2. 새 토큰 추가 → 네이밍 컨벤션 유지 (`status.*`, `flag.*` 등)
3. 변경 이력을 tokens.json의 `_meta`에 기록

### 새 원칙 추가
1. 적어도 3건의 실제 경험 근거 있어야 함
2. 기존 8개 원칙과 충돌하지 않는가?
3. `principles.md` 끝에 #N으로 추가, 번호는 재배치 금지
4. 반영된 구체 패턴/컴포넌트 링크

---

## 기존 프로젝트 → 라이브러리 환원 (Extraction)

### 시점
- 프로젝트 완료 직후 (기억이 살아있을 때)
- 실패 케이스 포함해서 기록 (Anti-패턴 보강)

### 방법
1. 해당 프로젝트의 `frontend/*.html`, `components/` 돌면서 반복 사용 요소 수집
2. 각 요소가 "이 프로젝트 한정"인지 "일반화 가능"인지 판정
3. 일반화 가능 → `01-components/` 또는 `02-patterns/`
4. 이 프로젝트 한정 → `instances/{project}/` 안에 기록

### 인스턴스 폴더 구조
```
instances/aiworld-harness/
├── README.md                        # 프로젝트 개요
├── flag-types-5.md                  # 이 프로젝트 고유 플래그 사전
├── rubric-label-dictionary.md       # 루브릭 id → 한글 매핑
├── domain-tone-guide.md             # 위인 멘토링 톤 가이드
└── component-types.md               # material/quiz/practice 등 도메인 타입
```

---

## 리뷰

### 정기
- 분기당 1회 라이브러리 리뷰 (원칙 위반된 사용 없나 점검)
- 새 프로젝트 시작 전 README · principles 재독

### 변경 후
- 파일 수정 시 해당 원칙·토큰 참조 링크가 깨지지 않았나 확인
- 예시 스크린샷이 outdated면 업데이트

---

## Deprecation

패턴이나 컴포넌트를 폐기할 때:
1. 상단에 `> **⚠ Deprecated** — since vX.X, replaced by [...].` 배너
2. 파일 삭제는 하지 않음 (참조 깨짐 방지)
3. 다음 major 버전에 정리

---

## 의사 결정 기록

큰 설계 결정이 있을 때:
- `docs/adr/` (Architecture Decision Records) 폴더에 타임스탬프로 기록
- 포맷: 문제 / 결정 / 근거 / 대안 / 영향

(현재는 미구현, 필요 시 추가)

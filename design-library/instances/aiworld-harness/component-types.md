# 컴포넌트 타입 5종 (AI World Harness)

이 프로젝트에서 생성되는 콘텐츠 컴포넌트 분류. 각각 schema·rubric·UI 프리뷰 렌더러가 다름.

---

## 1. `course_overview` — 과정 기획서

- **수량**: 코스당 1개
- **생성자**: Claude Opus 4.7
- **포함**: 코스명, 카테고리, 캐릭터명, 팔릴이유한줄, 프로젝트 결과물, 수강대상 3개, 수강효과 3개, 커리큘럼 10챕터 (가변)
- **UI**: 기획서 편집 가능 폼 (`showBlueprint`)
- **schema**: `schema-v1.json → definitions.course_overview`
- **rubric**: 7개 항목

## 2. `figure_rationale` — 위인 선정 배경

- **수량**: 코스당 1개
- **생성자**: GPT-5.4 → Claude 검증
- **포함**: opening_one_liner, figure_background, core_philosophy, topic_fit_reason, what_learner_gets (3~5), key_episodes (2~3)
- **UI**: 큰 인용문 + 섹션 여러 개 (previewFigureRationale)
- **schema**: `schema-v1.json → definitions.figure_rationale`
- **rubric**: 6개 항목

## 3. `material` — 학습자료

- **수량**: 챕터당 1개 (10챕터 = 10개)
- **생성자**: Claude → GPT 검증
- **포함**: 챕터당 6개 섹션 (도입·핵심개념·GBB·실전시나리오·체크리스트·요약), 1,500~2,500자
- **UI**: 섹션별 heading + kind badge + 본문 (previewMaterial)
- **schema**: `schema-v1.json → definitions.material_chapter`
- **rubric**: 10개 항목
- **내보내기**: xlsx 전체 + 개별 `.docx` 다운로드

## 4. `quiz` — 퀴즈

- **수량**: 챕터당 10문항 (기본) × 10챕터 = 100문항
- **생성자**: GPT → Claude 검증
- **유형 5종**: OX / 단일선택 / 복수선택 / 분류 / 단답형 (각 2문항)
- **포함**: 유형, 난이도, 제목 (N번째 수업 형식), 문제, 힌트, 보기, 정답, 분류명, 해설 (파이프 3단)
- **UI**: 문항 카드 10개 (previewQuiz)
- **schema**: `schema-v1.json → definitions.quiz_chapter_set`
- **rubric**: 19개 항목
- **내보내기**: xlsx 퀴즈 탭 (12컬럼)

## 5. `practice` — 실습

- **수량**: 챕터당 3문제 (기본) × 10챕터 = 30문제
- **생성자**: Claude → GPT 검증
- **3단계**: 실험 (기법 미사용 체감) / 레슨 (기법 적용 성공) / 도전 (심화 응용)
- **포함**: stage, 난이도, 합격점수, 콘텐츠명, 문제, 설명, good/better 정답, 평가항목 3개
- **UI**: 실습 카드 3개 (previewPractice)
- **schema**: `schema-v1.json → definitions.practice_chapter_set`
- **rubric**: 14개 항목
- **내보내기**: xlsx 실습 탭 (18컬럼)

---

## 수량 매트릭스

| 컴포넌트 | 수량 | 총합 |
|---|---|---|
| course_overview | 1 | 1 |
| figure_rationale | 1 | 1 |
| material | 챕터당 1 | 10 |
| quiz | 챕터당 10 | 100 |
| practice | 챕터당 3 | 30 |
| **컴포넌트 단위 합계** | | 22 |
| **콘텐츠 항목 합계** | | 142 |

> 사용자가 Control에서 parts / chapters_per_part / quiz_per_chapter / practice_per_chapter를 바꾸면 수량 전체 조정됨.

---

## 컴포넌트 lifecycle

```
[기획서 승인]
    ↓
figure_rationale ────── (단발)
    ↓
material × N ────────── (병렬 병렬)
    ↓ (앞 단계 material을 docText로 참조)
quiz × N   ────────────(병렬)
practice × N ──────────(병렬, 검증 실패 시 최대 3회 자동 재시도)
    ↓
run.completed → Review
```

---

## 재생성 흐름

- **항목 단위**: 퀴즈 1문제, 실습 1문제 — 플래그 카드에서 트리거
- **챕터 단위**: 해당 챕터의 material + quiz + practice 순차 재생성 — 프리뷰 헤더 버튼
- 각 재생성은 새 `component_id`로 저장, `parent_version` FK로 족보 추적

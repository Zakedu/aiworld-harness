# 루브릭 라벨 사전 (AI World Harness)

루브릭 id → "영역 · 항목" 친근 라벨 매핑. 플래그 카드에서 기술 id 대신 이 라벨을 표시.

소스: `frontend/index.html` 의 `RUBRIC_LOC` 객체.

---

## Course Overview

| rubric_id | 영역 | 항목 |
|---|---|---|
| overview.course_name.pattern | 과정 기획 | 코스명 형식 |
| overview.sell_reason.length | 과정 기획 | 팔릴 이유 한 줄 길이 |
| overview.targets.concrete | 과정 기획 | 수강 대상 구체성 |
| overview.effects.concrete | 과정 기획 | 수강 효과 구체성 |
| overview.curriculum.structure | 과정 기획 | 커리큘럼 난이도 순서 |
| overview.prompt_techniques.unique | 과정 기획 | 프롬프트 기법 중복 |
| overview.figure_topic.coherence | 과정 기획 | 위인-주제 연결성 |

## Figure Rationale (위인 선정 배경)

| rubric_id | 영역 | 항목 |
|---|---|---|
| rationale.background.factual | 위인 선정 배경 | 배경 사실성 |
| rationale.philosophy.specific | 위인 선정 배경 | 핵심 철학 구체성 |
| rationale.topic_fit.explicit_link | 위인 선정 배경 | 주제 연결고리 |
| rationale.episodes.sources_cited | 위인 선정 배경 | 에피소드 출처 |
| rationale.what_learner_gets.concrete | 위인 선정 배경 | 학습자 획득 역량 |
| rationale.voice.mentor_tone | 위인 선정 배경 | 멘토 톤 일관성 |

## Material (학습자료)

| rubric_id | 영역 | 항목 |
|---|---|---|
| material.sections.six_present | 학습자료 | 6개 섹션 구성 |
| material.length.1500_2500 | 학습자료 | 분량 1,500~2,500자 |
| material.good_better_best.present | 학습자료 | Good/Better/Best 비교 |
| material.checklist.5_to_7 | 학습자료 | 실전 체크리스트 5~7개 |
| material.opener.empathy_line_present | 학습자료 | 공감 오프너 (첫 섹션) |
| material.category.concept_explanation_present | 학습자료 | 전문 개념 설명 (SWOT 등) |
| material.templates.situation_specific_present | 학습자료 | 상황별 복붙 템플릿 |
| material.examples.concrete_and_practical | 학습자료 | 실제적 예시 |
| material.voice.mentor_persona | 학습자료 | 위인 화법 일관성 |
| material.no_error_outputs | 학습자료 | 출력물 오류 |
| material.bgb.bad_good_better_order | 학습자료 | Bad/Good/Better 3단 순서 |
| material.heading.better_prompt_fixed | 학습자료 | 소제목 "[ 더 좋은 프롬프트 만들기 ]" 포함 |
| material.heading.emoji_prefix | 학습자료 | 소제목 앞 이모지 |
| material.format.table_used | 학습자료 | 표 사용 |
| material.philosophy.practical_book | 학습자료 | 실용서적 톤 |
| material.philosophy.logic_strengthened | 학습자료 | 프롬프트 기법 > 말하기 논리 강화 |
| material.opener.tech_vs_plain_contrast | 학습자료 | 도입부 단순 vs 기법 대조 |
| material.bestseller_style.applied | 학습자료 | 베스트셀러 화법 적용 |

## Quiz (퀴즈)

| rubric_id | 영역 | 항목 |
|---|---|---|
| quiz.count.total_10 | 퀴즈 | 총 10문항 |
| quiz.count.type_each_2 | 퀴즈 | 유형별 2문항 |
| quiz.single.choices_4 | 퀴즈 · 단일선택 | 보기 4개 · 정답 1개 |
| quiz.multi.choices_5_answer_2 | 퀴즈 · 복수선택 | 보기 5개 · 정답 2개 |
| quiz.classification.partition_complete | 퀴즈 · 분류 | 5개 보기 완전 분배 |
| quiz.short_answer.hint_includes_initials | 퀴즈 · 단답형 | 힌트 초성 포함 |
| quiz.title.storytelling_format | 퀴즈 | 제목 — N번째 수업 형식 |
| quiz.question.scenario_based | 퀴즈 | 시나리오 기반 문제 |
| quiz.explanation.pipe_three_parts | 퀴즈 · 해설 | 파이프 3단 (정답/오답/실무) |
| quiz.explanation.ends_with_imnida | 퀴즈 · 해설 | 어미 '~입니다.' |
| quiz.single.question_suffix | 퀴즈 · 단일선택 | 문제 끝 '~가장 적절한 것은?' |
| quiz.multi.question_suffix | 퀴즈 · 복수선택 | 문제 끝 '2개 고르시오' |
| quiz.short_answer.question_suffix | 퀴즈 · 단답형 | 문제 끝 '쓰시오' |
| quiz.classification.question_suffix | 퀴즈 · 분류 | 문제 끝 '분류하시오' |
| quiz.hint.no_initials_for_non_short | 퀴즈 | 비단답형에 초성 금지 |
| quiz.single.distractors_plausible | 퀴즈 · 단일선택 | 오답 그럴듯함 |
| quiz.table.schema_strict | 퀴즈 | 12컬럼 서식 준수 |
| quiz.persona_consistency | 퀴즈 · 해설 | 위인 페르소나 유지 |
| quiz.no_content_bleed | 퀴즈 | 학습자료 근거 밖 내용 유입 |
| quiz.philosophy.understand_over_trap | 퀴즈 | 이해 중심 (트릭 출제 X) |
| quiz.philosophy.not_parroting_material | 퀴즈 | 학습자료 단순 복기 금지 |
| quiz.philosophy.prompt_writing_check | 퀴즈 | 프롬프트 작성 체크 질문 |
| quiz.hint.pre_submit_role | 퀴즈 · 힌트 | 제출 전 유추 정보 역할 |
| quiz.explanation.friendly_post_submit | 퀴즈 · 해설 | 친절한 설명 3요소 |

## Practice (실습)

| rubric_id | 영역 | 항목 |
|---|---|---|
| practice.count.three_stages | 실습 | 3단계 (실험/레슨/도전) |
| practice.difficulty.progression | 실습 | 난이도 순서 |
| practice.passing_score.progression | 실습 | 합격점수 순서 |
| practice.problem.has_concrete_context | 실습 · 문제 | 구체 맥락 (단일 키워드 금지) |
| practice.answer.format_is_prompt_example | 실습 · 정답 | good/better 프롬프트 형식 |
| practice.hint.includes_concrete_example | 실습 · 힌트 | 구체 예시 정보 |
| practice.title.figure_stage | 실습 · 콘텐츠명 | {위인} + 단계 포함 |
| practice.question.figure_voice_and_suffix | 실습 · 문제 | 위인 화법 + '~하시오' |
| practice.criteria.all_suffix_q | 실습 · 평가항목 | 모두 '~했나요?' 어미 |
| practice.description.principle_and_stars | 실습 · 설명 | 위인 원칙 + '*' 구분 |
| practice.stage1.weak_prompt | 실습 1 (실험) | 의도적 약한 프롬프트 |
| practice.stage3.compound_prompt | 실습 3 (도전) | 복합 조건 프롬프트 |
| practice.table.schema_strict | 실습 | 18컬럼 서식 준수 |
| practice.fixed_values | 실습 | 고정값 (환경·형식 등) |
| practice.title.self_contained | 실습 · 콘텐츠명 | 제목만 보고 이해 가능 |
| practice.description.examples_2plus | 실습 · 설명 | 구체 예시 2개 이상 |
| practice.title.length_40_100 | 실습 · 콘텐츠명 | 길이 40~100자 |
| practice.description.length_94_140 | 실습 · 설명 | 길이 94~140자 |
| practice.criteria.title_max_20 | 실습 · 평가항목 | 제목 최대 20자 |
| practice.criteria.description_max_40 | 실습 · 평가항목 | 설명 최대 40자 |
| practice.criteria.distinct_3 | 실습 · 평가항목 | 서로 다른 3가지 기준 |
| practice.passing_scores.default_50_80_80 | 실습 | 기본 합격점수 50/80/80 |

---

## 작성 기준 (새 루브릭 추가 시)

- **영역**: 컴포넌트 타입 한글 (학습자료 / 퀴즈 / 실습 등). 세부 구역 있으면 ` · ` 구분 (예: `퀴즈 · 해설`)
- **항목**: 12자 이내, 명사구, 구체적. "무엇을 보는 규칙인지" 한 번에 와닿게
- raw id에서 마지막 점(.) 뒤만 한글화하는 경우가 많음. 단, 너무 짧으면 영역을 보강

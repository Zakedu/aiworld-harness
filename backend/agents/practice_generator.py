"""
Practice Generator — 챕터 1개의 실습 3문제 세트 (실험/레슨/도전).

원본: aiworld-main/prompts/practice-generator.md + .claude/skills/practice-generator/SKILL.md
추가 반영: 진규·재정 피드백 (구체 맥락·프롬프트 예시 정답·구체 힌트·하난이도 0점 허용)
"""
from __future__ import annotations
from .base import call_model
from ..prompts_store import resolve as resolve_prompt

SYSTEM_PROMPT = """[오염 방지 규칙 — 최우선 적용]
이 SYSTEM_PROMPT 안의 예시("고속터미널"·"한식당 추천"·"30대 직장인" 등)는 형식 시연용이다.
실제 문제·정답·힌트는 반드시 blueprint의 character_name·topic·learner_persona 기반으로 생성하라.
다른 코스 시나리오를 그대로 복붙하면 즉시 FAIL.

당신은 AI 프롬프트 실습을 설계하는 교육 콘텐츠 기획자입니다.
학습자가 프롬프트 기법의 효과를 직접 체감하도록 3단계 실습 여정을 설계합니다.

# 실습 설계 철학 — 3단계 깊이

챕터당 실습 3개는 각자 다른 목적을 갖는다:

1. **첫 번째 실습 = '경각심' 용**
   - 해당 챕터 프롬프트 기법을 **활용하지 않은** 상태의 실습
   - 기법 없이 대충 프롬프트를 입력했을 때의 한계를 직접 느끼게 해 "이 기법을 제대로 배워야겠다"는 각성을 유도
   - 간단하고 쉬운 문제
2. **두 번째 실습 = '평이한 정답' 수준**
   - 두루뭉술한 평이한 정답 프롬프트로도 통과할 수 있는 수준
3. **세 번째 실습 = '구체적 정답' 수준**
   - 더 복잡하고 구체적인 정답 프롬프트까지 써야 정답으로 인정되는 수준

# 핵심 콘셉트: 3단계 실습 여정

| 단계 | 이름 | 목적 |
|---|---|---|
| 실습 1 | {위인}의 실험 | 기법 미사용 → 한계 체감 (경각심) |
| 실습 2 | {위인}의 레슨 | 기법 적용 → 평이한 정답 성공 |
| 실습 3 | {위인}의 도전 | 심화 응용 → 구체적 정답 |

# 실습 문제 작성 원칙 (절대 규칙)
1. **'제목'만 보고도 이해 가능해야 한다** — 수강생이 설명을 읽지 않아도 "이걸 해야 하는구나, 이 프롬프트를 입력해야 하는구나"를 즉시 파악할 수 있어야 한다.
2. **'설명'은 제목과 중복 금지** — 제목에 이미 있는 내용 반복 X. **구체 예시 2개 이상**을 넣는다.
3. **'정답'은 수강생이 제목·설명만 보고 입력 가능한 수준의 모범 답안 프롬프트**. 너무 이상적이거나 전문가 수준은 금지.
4. **평가항목 3개는 서로 다른 기준**이어야 한다. 같은 관점 반복 금지.

# 각 실습 규칙

## 실습 1 — 경각심용 (난이도 하|중하)
- 합격점수: **50점 (기본)** — "대충 써도 넘어가는 장치". 0점도 허용 가능.
- **BAD 프롬프트 정의**: 맥락 0 + 역할 0 + 형식 0 수준
  - 나쁜 예 (금지): "시장 분석 보고서 써줘 (배경: 전기차)" → 이미 맥락이 있어서 BAD가 아님
  - 올바른 BAD 예: "시장 분석 보고서 써줘" → 맥락도 역할도 형식도 전혀 없는 순수 명령
  - BAD 프롬프트의 합격점수는 0~50점 (한계 체감 목적)
- 콘텐츠명(title): **행동 중심 명사형** (40~100자). "위인의 실험 —" 같은 위인명 접두 패턴 **금지**.
  - 이 실습이 *무엇을 하는지*가 제목에서 직접 읽혀야 한다.
  - 예) "맥락 없이 보고서를 요청해 AI 한계 확인하기" (O) / "갈릴레오의 실험 — 보고서 요청" (X)
- 문제(question): 구체적 과제 지시 + "~하시오." 또는 "~하세요." 어미 (40~100자)
- 설명(description): "*" 기호로 조건 구분. **반드시 구체 예시 2개 이상 포함** (94~140자)
- 정답(answer): **의도적으로 약한 프롬프트** (기법 미적용). 수강생이 제목·설명만 보고 그대로 입력할 수 있는 수준.
- 평가항목 3개 (서로 다른 기준):
  - "기법 없이 단순하게 요청했나요?"
  - "AI의 부족한 답변을 관찰할 수 있는 형태인가요?"
  - "이 실습의 한계를 체감할 수 있는 요청인가요?"

## 실습 2 — 평이한 정답 수준 (난이도 중)
- 합격점수: **80점 (기본)**
- 콘텐츠명(title): **행동 중심 명사형** (40~100자). "위인의 레슨 —" 접두 패턴 **금지**.
  - 예) "역할·독자·목적 3요소를 넣어 보고서 초안 작성하기" (O) / "갈릴레오의 레슨 — 역할 부여" (X)
- 문제: 구체적 과제 지시 + "~하시오." (40~100자)
- 설명: 적용해야 할 기법의 핵심 조건 명시 + **구체 예시 2개 이상** (94~140자)
- 정답: 기법 핵심 조건 반영. **두루뭉술한 평이한 정답으로도 통과 가능한 수준**. good/better 2단 예시.
- 평가항목 3개 (서로 다른 기준):
  - "{프롬프트기법}의 핵심 요소를 포함했나요?"
  - "구체적 맥락/조건을 명시했나요?"
  - "결과물 형태를 요청했나요?"

## 실습 3 — 구체적 정답 수준 (난이도 상|중상)
- 합격점수: **80점 (기본)** — 기본은 80. 고난도 시 85도 허용.
- 콘텐츠명(title): **행동 중심 명사형** (40~100자). "위인의 도전 —" 접두 패턴 **금지**.
  - 예) "상황·페르소나·출력형식 복합 조건으로 심층 분석 보고서 완성하기" (O) / "갈릴레오의 도전 — 심화 적용" (X)
- 문제: 복잡한 상황 포함 + "~하시오." (40~100자)
- 설명: 복잡한 상황 + 여러 조건 조합 + **구체 예시 2개 이상** (94~140자)
- 정답: **더 복잡하고 구체적인 정답 프롬프트까지 써야 정답으로 인정**. 복합 조건(상황+페르소나+출력형식).
- 평가항목 3개 (서로 다른 기준):
  - "복잡한 상황/맥락을 포함했나요?"
  - "페르소나 또는 역할을 설정했나요?"
  - "구체적 출력 형식을 지정했나요?"

# 길이·어미 규칙 (엄격 준수)
- 문제 제목(title): **40~100자** (공백 포함), 어미 "~하시오." 또는 "~하세요."
- 문제 설명(description): **94~140자**, 제목과 중복 금지, **예시 2개 이상**
- 평가항목 제목: **최대 20자**, 어미 **"~했나요?"** 통일
- 평가항목 설명: **최대 40자**

# 5개 과정 피드백 기반 필수 규칙

1. **문제(question)에 반드시 구체 예시·맥락 포함. 단일 키워드 문제 절대 금지.**
   - 나쁜 예: "페르소나를 활용해 고속터미널 맛집을 찾는 프롬프트를 작성하시오."
   - 좋은 예: "30대 직장인이 평일 저녁 고속터미널에서 한식 모임 장소를 찾는 상황이다. 페르소나 기법을 활용해 더 정확한 추천을 받는 프롬프트를 작성하시오."

2. **정답(answer)은 반드시 "프롬프트 good / better 2단 예시" 형태.** 가이드 문장형 정답 금지.
   ```
   [Good]
   당신은 한식당 추천 전문가입니다. 고속터미널 근처 한식 모임 장소 추천해주세요.

   [Better]
   당신은 서울 고속터미널 일대 한식당을 10년 이상 안내한 로컬 가이드입니다.
   30대 직장인 6명이 평일 저녁 7시에 2시간 식사할 예정입니다.
   분위기는 조용하고, 예산은 1인 3만원 이내입니다.
   도보 5분 이내 한식당 3곳을 이름·대표 메뉴·예약 필요 여부와 함께 표로 정리해주세요.
   ```

3. **힌트는 프롬프트 작성에 즉시 쓸 수 있는 구체 예시 정보 포함.** 개념 설명만으론 불합격.

4. **실습 1 정답은 반드시 맥락 0, 역할 0, 형식 0 수준의 프롬프트여야 함.**
   나쁜 예: "30대 직장인 상황에서 마케팅 보고서 써줘" (맥락이 이미 있음 → BAD가 아님)
   좋은 예: "마케팅 보고서 써줘" (아무 맥락 없는 순수 명령 → 진짜 BAD)

5. 실습 3 정답은 상황+페르소나+출력형식 복합 조합 프롬프트.

6. **learning_point는 "이 실습이 검증하는 학습 능력"을 1줄로 명시한다.**
   - 실습 1: "맥락 없는 프롬프트의 한계를 체감할 수 있는가"
   - 실습 2: "{기법명}의 핵심 요소를 프롬프트에 적용할 수 있는가"
   - 실습 3: "{기법명}을 복합 조건(상황+역할+형식)으로 구현할 수 있는가"

# 공통 필드 고정값 (절대 변경 금지)
- environment: "ChatGPT"
- response_type: "텍스트"
- is_free: "FALSE"
- clip_group_id: "-"
- file_url: "-"
- practice_role: "BAD" (stage=실험) | "GOOD" (stage=레슨 또는 도전) — SQL extras.practice_role로 사용

# 품질 체크리스트 (출력 전 Self-Check)
- [ ] 3문제 모두 생성? 순서 [실험,레슨,도전]?
- [ ] 난이도 하|중하 → 중 → 상|중상 순서?
- [ ] 합격점수 0~55 → 75 → 80~85 순서?
- [ ] 콘텐츠명에 "{위인} + 단계" 포함?
- [ ] 문제에 구체 과제 지시 + "~하시오." 어미?
- [ ] 문제가 단일 키워드 아니라 구체 맥락 포함?
- [ ] 정답이 good/better 2단 프롬프트 예시?
- [ ] 힌트가 구체 예시 정보 포함?
- [ ] 설명에 "*" 기호 조건 구분?
- [ ] 평가항목 3개 제목 모두 "~했나요?" 어미?
- [ ] 고정값(환경/응답형식/파일URL 등) 정확?
- [ ] learning_point 3개 모두 작성? 각각 단계 목적에 맞는가?
- [ ] practice_role: 실험=BAD, 레슨/도전=GOOD 적용?
- [ ] 실습 1 정답이 진짜 맥락 0/역할 0/형식 0 수준인가?

# 출력 JSON (반드시 이 구조)
{
  "chapter_id": "1-1",
  "items": [
    {
      "chapter_id": "1-1",
      "clip_group_id": "-",
      "is_free": "FALSE",
      "stage": "실험" | "레슨" | "도전",
      "learning_point": "이 실습이 검증하는 핵심 학습 포인트 1줄 (예: 맥락 없는 프롬프트의 한계를 직접 체감할 수 있는가)",
      "practice_role": "BAD",
      "title": "...",
      "question": "...",
      "description": "*조건1\\n*조건2\\n*예시1: ...\\n*예시2: ...",
      "file_url": "-",
      "environment": "ChatGPT",
      "difficulty": "상|중상|중|중하|하",
      "answer": "[Good]\\n...\\n\\n[Better]\\n...",
      "passing_score": 0|50|55|75|80|85,
      "response_type": "텍스트",
      "criteria": [
        {"title": "~했나요?", "description": "..."},
        {"title": "~했나요?", "description": "..."},
        {"title": "~했나요?", "description": "..."}
      ]
    },
    ... 정확히 3개 (실험 → 레슨 → 도전 순)
  ]
}
"""


def _user_prompt(chapter: dict, blueprint: dict, material_excerpt: str, mixer: dict) -> str:
    fb = (mixer or {}).get("_user_feedback") or ""
    fb_block = f"\n[사용자 피드백 — 이번 재생성 시 반드시 반영]\n{fb}\n" if fb else ""
    n = int((mixer or {}).get("practice_per_chapter", 3))
    ai_tool = (mixer or {}).get("target_ai_tool") or "ChatGPT"
    return (
        f"[과정]\n코스명: {blueprint.get('course_name')}\n"
        f"위인: {blueprint.get('character_name')}\n\n"
        f"[이번 챕터]\n"
        f"챕터: {chapter['chapter_id']} — {chapter['chapter_name']}\n"
        f"파트: {chapter['part_name']}\n"
        f"프롬프트 기법: {chapter['prompt_technique']}\n\n"
        f"[학습자료 본문 (docText) — 유일한 근거]\n{material_excerpt}\n\n"
        f"[이번 실습 수량] 정확히 {n}문제"
        f"{' (stage: 실험→레슨→도전 3단계 유지)' if n == 3 else ' (3단계 스토리: 실험/레슨/도전을 비율에 맞춰 배분)'}\n"
        f"[타깃 AI 도구] 모든 모범 프롬프트와 고정값 environment는 '{ai_tool}' 기준으로 작성\n"
        f"[결과값 조절]\n"
        f"프롬프트 서식 레벨: {mixer.get('prompt_level', 'good/better 2단')}\n"
        f"힌트 상세도: {mixer.get('hint_detail', '표준')}\n"
        f"하 난이도 합격컷 허용 범위: {mixer.get('low_pass_min', 0)}점~\n"
        f"{fb_block}\n"
        f"위 조건으로 실습 {n}문제를 위 출력 JSON 구조로 반환하라."
    )


async def generate_practice_chapter(
    chapter: dict,
    blueprint: dict,
    material_excerpt: str,
    mixer: dict,
    provider: str = "claude",
) -> dict:
    user = _user_prompt(chapter, blueprint, material_excerpt, mixer)
    sys = resolve_prompt("practice_generator", SYSTEM_PROMPT)
    return await call_model(provider, sys, user, json_mode=True, temperature=0.6)  # type: ignore


async def regenerate_practice_item(
    original_item: dict,
    blueprint: dict,
    chapter: dict,
    sibling_items: list[dict],
    user_instruction: str,
    flag_reason: str,
    provider: str = "claude",
) -> dict:
    """단일 실습 항목 재생성 — 기획서·형제 항목·수정 지시를 모두 상속."""
    import json
    siblings = json.dumps(sibling_items, ensure_ascii=False, indent=2)
    user = (
        f"[과정]\n코스명: {blueprint.get('course_name')}\n"
        f"위인: {blueprint.get('character_name')}\n"
        f"챕터: {chapter['chapter_id']} {chapter['chapter_name']}\n"
        f"프롬프트 기법: {chapter['prompt_technique']}\n\n"
        f"[재생성 대상 — 직전 버전]\n{json.dumps(original_item, ensure_ascii=False, indent=2)}\n\n"
        f"[동일 챕터 형제 항목(난이도 단계 + 스토리 흐름 유지)]\n{siblings}\n\n"
        f"[플래그 사유]\n{flag_reason}\n\n"
        f"[사용자 수정 지시]\n{user_instruction}\n\n"
        "이 1개 항목만 — 시스템 프롬프트의 모든 규칙을 지키며 — 단일 item JSON 오브젝트로 재작성하라. "
        "전체 배열이 아닌 단일 오브젝트 출력. 원 stage/난이도는 유지(사용자가 명시적으로 변경 지시하지 않으면)."
    )
    sys = resolve_prompt("practice_generator", SYSTEM_PROMPT)
    return await call_model(provider, sys, user, json_mode=True, temperature=0.6)  # type: ignore

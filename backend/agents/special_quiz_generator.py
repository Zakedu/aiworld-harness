"""
Special Quiz Generator — 파트 티저 / 파트 종합 / 최종 회고 퀴즈 생성.

파트 티저 (teaser):       파트 시작 전 호기심 유발 3문항
파트 종합 (part_summary): 파트 내 모든 챕터 기법 교차 통합 5문항
최종 회고 (final_review): 전 파트 통합 10문항 최종 평가
"""
from __future__ import annotations
from .base import call_model

# ── 공통 해설 형식 주의사항 ─────────────────────────────
_EXPL_RULE = """\
# 해설 형식 (반드시 준수)
"정답 설명 ~입니다. | 오답 피드백 ~입니다. | 실무 팁 ~입니다." (파이프 3단, ~입니다. 어미)
위인 화법(라네/지네/일세) 금지. 학습자 관점으로만 작성.
"""

# ══════════════════════════════════════════════════════
# 파트 티저
# ══════════════════════════════════════════════════════
_TEASER_SYS = f"""당신은 AI 프롬프트 강의의 파트 티저 퀴즈를 만드는 교육 설계자입니다.

# 목적
학습자가 파트를 시작하기 전 흥미를 갖도록 직관/경험만으로 도전할 수 있는 3문항 예고편 퀴즈.
"이걸 배우면 이런 게 가능해진다"는 기대감을 심는 것이 핵심.

# 규칙
- 정확히 3문항 (OX 1 / 단일선택 1 / 단답형 1)
- 아직 배우지 않아도 직관으로 시도할 수 있는 수준 (난이도: 하/중하)
- hint: "이 파트를 배우면 확실히 알 수 있어요!" 스타일
- explanation 마지막 문장: "이 파트에서 자세히 배웁니다." 로 마무리
{_EXPL_RULE}

# 출력 JSON
{{
  "quiz_role": "teaser",
  "part_id": "{{part_id}}",
  "part_name": "{{part_name}}",
  "items": [
    {{
      "chapter_id": "{{part_id}}-티저",
      "clip_group_id": "-",
      "is_free": "TRUE",
      "type": "OX" | "단일선택" | "단답형",
      "difficulty": "하" | "중하",
      "title": "파트 {{N}} 예고 — {{호기심 유발 부제}}",
      "question": "...",
      "hint": "이 파트를 배우면 확실히 알 수 있어요!",
      "choices": "-" 또는 "(1) ...\\n(2) ...\\n(3) ...\\n(4) ...",
      "answer": "...",
      "category": "-",
      "explanation": "... | ... | ...이 파트에서 자세히 배웁니다."
    }}
    /* 총 3개 */
  ]
}}
"""

# ══════════════════════════════════════════════════════
# 파트 종합
# ══════════════════════════════════════════════════════
_PART_SUMMARY_SYS = f"""당신은 AI 프롬프트 강의의 파트 종합 퀴즈를 만드는 교육 설계자입니다.

# 목적
파트 내 모든 챕터의 프롬프트 기법을 교차 비교하는 5문항 통합 복습 퀴즈.

# 규칙
- 정확히 5문항 (OX 1 / 단일선택 2 / 복수선택 1 / 단답형 1)
- 각 문항은 **파트 내 서로 다른 챕터의 기법을 비교**하는 통합형
- 단일 챕터 내용만 묻는 문항 금지 — 반드시 2개 이상 챕터 기법 연결
- 난이도: 중 이상 (중 2 / 중상 2 / 상 1)
- 복수선택: 보기 5개 / 정답 2개 고정
{_EXPL_RULE}

# 출력 JSON
{{
  "quiz_role": "part_summary",
  "part_id": "{{part_id}}",
  "part_name": "{{part_name}}",
  "items": [
    {{
      "chapter_id": "{{part_id}}-종합",
      "clip_group_id": "-",
      "is_free": "TRUE",
      "type": "OX" | "단일선택" | "복수선택" | "단답형",
      "difficulty": "중" | "중상" | "상",
      "title": "파트 {{N}} 종합 — {{교차 비교 포인트}}",
      "question": "...",
      "hint": "...",
      "choices": "-" 또는 "(1) ...\\n...",
      "answer": "...",
      "category": "-",
      "explanation": "... | ... | ..."
    }}
    /* 총 5개 */
  ]
}}
"""

# ══════════════════════════════════════════════════════
# 최종 회고
# ══════════════════════════════════════════════════════
_FINAL_REVIEW_SYS = f"""당신은 AI 프롬프트 강의의 최종 회고 퀴즈를 만드는 교육 설계자입니다.

# 목적
전 파트 프롬프트 기법을 통합하여 실무 적용 역량을 검증하는 10문항 최종 평가.

# 규칙
- 정확히 10문항 (OX 2 / 단일선택 2 / 복수선택 2 / 분류 2 / 단답형 2)
- 각 문항은 **서로 다른 파트의 기법을 교차 비교**하는 통합형. 단일 파트 금지.
- 실무 시나리오 기반 — "이 상황에서 어떤 기법이 가장 적합한가?" 형식 권장
- 난이도: 중 3 / 중상 4 / 상 3
- 복수선택: 보기 5개 / 정답 2개. 분류: 보기 5개 완전 분배.
{_EXPL_RULE}

# 출력 JSON
{{
  "quiz_role": "final_review",
  "part_id": "final",
  "part_name": "최종 회고",
  "items": [
    {{
      "chapter_id": "final-회고",
      "clip_group_id": "-",
      "is_free": "TRUE",
      "type": "OX" | "단일선택" | "복수선택" | "분류" | "단답형",
      "difficulty": "중" | "중상" | "상",
      "title": "최종 회고 {{N}}번 — {{통합 비교 포인트}}",
      "question": "...",
      "hint": "...",
      "choices": "-" 또는 "(1) ...\\n...",
      "answer": "...",
      "category": "-" 또는 "분류명1, 분류명2",
      "explanation": "... | ... | ..."
    }}
    /* 총 10개 */
  ]
}}
"""


# 설정 화면용 대표 프롬프트 (3개 역할 프롬프트 헤더 포함)
SYSTEM_PROMPT = (
    "# 특수 퀴즈 생성기 — 3가지 역할\n\n"
    "## [1] 파트 티저 (teaser · 3문항)\n" + _TEASER_SYS + "\n\n"
    "## [2] 파트 종합 (part_summary · 5문항)\n" + _PART_SUMMARY_SYS + "\n\n"
    "## [3] 최종 회고 (final_review · 10문항)\n" + _FINAL_REVIEW_SYS
)


def _part_context(part_name: str, chapters: list[dict], excerpts: dict[str, str]) -> str:
    lines = [f"[파트: {part_name}]"]
    for ch in chapters:
        cid = ch["chapter_id"]
        lines.append(f"\n챕터 {cid} — {ch['chapter_name']} (기법: {ch.get('prompt_technique', '')})")
        ex = excerpts.get(cid, "")
        if ex:
            lines.append(ex[:500])
    return "\n".join(lines)


async def generate_part_teaser(
    part_id: str,
    part_name: str,
    chapters: list[dict],
    blueprint: dict,
    provider: str = "claude",
) -> dict:
    user = (
        f"코스명: {blueprint.get('course_name')}\n"
        f"파트: {part_id} — {part_name}\n"
        f"이 파트에서 배울 기법: {', '.join(ch.get('prompt_technique', '') for ch in chapters)}\n\n"
        "티저 퀴즈 3문항을 출력 JSON으로 반환하라."
    )
    return await call_model(provider, _TEASER_SYS, user, json_mode=True, temperature=0.7)  # type: ignore


async def generate_part_summary(
    part_id: str,
    part_name: str,
    chapters: list[dict],
    blueprint: dict,
    material_excerpts: dict[str, str],
    provider: str = "claude",
) -> dict:
    ctx = _part_context(part_name, chapters, material_excerpts)
    user = (
        f"코스명: {blueprint.get('course_name')}\n\n"
        f"{ctx}\n\n"
        "파트 종합 퀴즈 5문항을 출력 JSON으로 반환하라."
    )
    return await call_model(provider, _PART_SUMMARY_SYS, user, json_mode=True, temperature=0.5)  # type: ignore


async def generate_final_review(
    blueprint: dict,
    all_parts: list[dict],
    provider: str = "claude",
) -> dict:
    lines: list[str] = []
    for p in all_parts:
        lines.append(f"\n[파트 {p['part_id']}: {p['part_name']}]")
        for ch in p["chapters"]:
            lines.append(f"  챕터 {ch['chapter_id']} — {ch['chapter_name']} (기법: {ch.get('prompt_technique', '')})")
    user = (
        f"코스명: {blueprint.get('course_name')}\n"
        f"전체 파트 구성:\n{''.join(lines)}\n\n"
        "최종 회고 퀴즈 10문항을 출력 JSON으로 반환하라."
    )
    return await call_model(provider, _FINAL_REVIEW_SYS, user, json_mode=True, temperature=0.5)  # type: ignore

"""LLM-as-judge — 루브릭 YAML 항목별 상/중/하 판정."""
from __future__ import annotations
import json
import yaml  # type: ignore
from typing import Any
from ..config import RUBRIC_PATH, RUBRIC_OVERALL_PASS
from ..agents.base import call_model

_rubric_cache = None  # type: ignore


def _load_rubric() -> dict:
    global _rubric_cache
    if _rubric_cache is None:
        _rubric_cache = yaml.safe_load(RUBRIC_PATH.read_text(encoding="utf-8"))
    return _rubric_cache


def _items_for(component_type: str) -> list[dict]:
    rubric = _load_rubric()
    mapping = {
        "course_overview": "course_overview",
        "figure_rationale": "figure_rationale",
        "material": "material",
        "quiz": "quiz",
        "practice": "practice",
    }
    key = mapping.get(component_type, component_type)
    return rubric["components"].get(key, [])


# ============================================================
# 컴포넌트 타입별 검증자 시스템 프롬프트 5종
# (Admin 페이지에서 override 가능)
# ============================================================

_BASE_OUTPUT_FORMAT = """
각 항목을 PASS / MARGINAL / FAIL 중 하나로 판정:
- PASS: 요구조건 충족
- MARGINAL: 애매하게 걸침, 사람 확인 필요
- FAIL: 명백히 미충족

판정 시 '구체적 근거 (어느 필드·문장이 왜 그런 판정인지)'를 evidence에 서술.

출력은 JSON:
{
  "results": [
    {"id": <루브릭 항목 id>, "verdict": "PASS"|"MARGINAL"|"FAIL", "evidence": "..."},
    ...
  ],
  "overall_score": 0~100   (PASS=1, MARGINAL=0.5, FAIL=0 → 평균×100)
}
"""

COMPONENT_VALIDATOR_PROMPTS: dict[str, str] = {

    "course_overview": """당신은 AI 교육 **코스 기획서** 품질 평가자입니다.

[평가 관점]
- 코스명 네이밍 패턴("{위인}의 {동사} — {부제목}") 준수 여부
- 수강대상·수강효과가 추상적이지 않고 구체적 어려움/변화를 묘사하는지
- 커리큘럼이 기초→심화→종합 순서로 배치됐는지
- 프롬프트 기법이 중복 없이 배정됐는지
- 위인의 교육 철학과 주제가 자연스럽게 연결됐는지

[엄격도] 본 단계가 전체 파이프라인의 기초이므로 중·상 심각도 항목은 엄격히 판정.
""" + _BASE_OUTPUT_FORMAT,

    "figure_rationale": """당신은 **위인 선정 배경** 품질 평가자입니다.

[평가 관점]
- 위인 배경·철학이 실제 사실 기반인가 (허구 금지)
- 철학과 주제(프롬프트 기법) 간 연결고리가 추상 미덕이 아닌 구체 매핑인가
- 에피소드마다 출처(서적·기사·연도) 명시됐는가
- 학습자가 얻는 것이 추상 역량이 아닌 실무 행동으로 기술됐는가
- 멘토 톤과 교과서적 설명체가 섞이지 않았는가

[엄격도] 출처·사실 관련 항목은 FAIL 판정 우선. 톤 관련은 MARGINAL 우선.
""" + _BASE_OUTPUT_FORMAT,

    "material": """당신은 **학습자료** (실용서적 형태) 품질 평가자입니다.

[평가 관점]
- 7개 섹션 구조 (배경지식·도입·핵심개념·Bad/Good/Better·실전시나리오·체크리스트·요약) 준수
- 배경지식(S1): [위인 도메인 핵심 지식] → [도메인 문제] → [이 프롬프트 기법이 해법인 이유] 3단 흐름인지 확인
- `[ 더 좋은 프롬프트 만들기 ]` 소제목 정확히 포함
- **Bad → Good → Better 3단** (Good/Better/Best 아님) 실제 서술, `=== Bad ===` 마커만 허용 (괄호 설명 추가 금지)
- 소제목 앞 이모지 아이콘
- 마크다운 표 최소 1개 사용
- 도입부(empathy_opener)가 공감 오프너로 시작하고 단순 vs 기법 대조 장면 포함
- 핵심 개념에 카테고리별 전문 개념(SWOT 등) 명시
- 실전 시나리오에 상황별 복붙 템플릿
- "뻔한 좋은 이야기" 배제 — 구체 인사이트·수치·실패담 포함
- **empathy_opener 이후 섹션에서 위인 화법 없음** — 학습자 관점 중심 (라네/이라네/일세 등 금지)

[엄격도] 실용서적·교과서적 이야기 금지 원칙은 엄격. 논리가 약하면 FAIL.
""" + _BASE_OUTPUT_FORMAT,

    "quiz": """당신은 **퀴즈** 품질 평가자입니다. "수강생이 학습자료를 이해했는지" 확인하는 관점.

[평가 관점]
- 총 10문항 (또는 지정 수량) + 5유형(OX/단일/복수/분류/단답형) 분포
- 유형별 정답 형식 (단일선택 4보기·복수선택 5보기 2정답·분류 완전분배·단답형 초성힌트)
- 문제 어미 (~가장 적절한 것은? / 2개 고르시오 / ~로 분류하시오 / 빈칸에 들어갈 단어를 쓰시오)
- 제목이 "{위인}의 N번째 수업 — 스토리텔링" 형식
- 문제가 시나리오 기반 (학술적 문장 금지)
- **해설이 파이프(|) 3단 구조 + "~입니다." 어미**
- 힌트는 정답 유추 정보 (정답 직접 노출 금지, 제출 전 역할)
- 해설은 정답 이유·오답 피드백·실무 팁 3요소 포함 (제출 후 친절한 설명)
- 학습자료 근거 밖 내용 유입 없음, 학습자료를 단순 복기하지 않고 응용

[엄격도] 서식·어미 항목은 FAIL 엄격. 이해 중심 철학 항목은 MARGINAL 우선.
""" + _BASE_OUTPUT_FORMAT,

    "practice": """당신은 **실습** 품질 평가자입니다. "수강생이 프롬프트 기법을 체감하고 실전 적용"하게 설계됐는지.

[평가 관점]
- 3단계(실험/레슨/도전) 순서 + 난이도·합격점수 (기본 50/80/80)
- 문제 제목이 40~100자, 설명이 94~140자, 평가항목 제목 ≤20자 / 설명 ≤40자
- **제목만 보고 이해 가능** (설명 없이)
- 설명에 **구체 예시 2개 이상** (제목과 중복 금지)
- 문제에 구체 맥락 포함 (단일 키워드 문제 금지)
- 정답이 "프롬프트 good/better 2단 예시" 형태 (가이드 문장형 정답 금지)
- 힌트에 프롬프트 작성용 구체 예시 정보 포함 (개념 설명만으로 불합격)
- 평가항목 3개가 서로 다른 기준, 모두 "~했나요?" 어미
- 고정값 (ChatGPT, 텍스트, is_free=FALSE, clip_group_id=-, file_url=-) 준수

[엄격도] 제목 자가완결성·정답 프롬프트 형식은 FAIL 엄격. 길이 일탈은 MARGINAL.
""" + _BASE_OUTPUT_FORMAT,

    "story": """당신은 **스토리** (위인 멘토링 서사) 품질 평가자입니다.

[평가 관점]
- 위인 화법이 자연스럽고 일관됨 (교과서체·설명체 아님)
- 스토리가 해당 챕터 프롬프트 기법과 실질적으로 연결됨
- 학습자가 감정적으로 공감할 수 있는 구체 상황·에피소드 포함
- 위인의 역사적 맥락·철학이 왜곡 없이 반영됨
- 스토리 안에서 "기법 미적용 → 적용 후 변화"의 흐름이 느껴짐

[엄격도] 위인 사실 왜곡은 FAIL 엄격. 감성적 연결이 약하면 MARGINAL.
""" + _BASE_OUTPUT_FORMAT,

    "special_quiz": """당신은 **특수 퀴즈** (파트 티저/종합/최종 회고) 품질 평가자입니다.

[평가 관점]
- quiz_role(teaser/part_summary/final_review)에 맞는 문항 수 준수 (티저=3, 종합=5, 회고=10)
- 각 문항에 question/answer/explanation 모두 존재
- 역할별 유형 믹스 준수 (티저=OX+단일+단답, 종합/회고=복수+분류 포함)
- 파트 티저·종합은 해당 파트 챕터 내용만 다룸 (타 파트 내용 혼입 금지)
- 해설이 정답 이유 + 실무 팁 포함 (단순 정답 반복 금지)
- 학습자료 근거 밖 수치·사례·주장 없음

[엄격도] 문항 수·필수 필드는 FAIL 엄격. 유형 믹스 일탈은 MARGINAL.
""" + _BASE_OUTPUT_FORMAT,
}


def _get_validator_prompt(component_type: str) -> str:
    """override 있으면 그것, 없으면 COMPONENT_VALIDATOR_PROMPTS[type]."""
    from ..prompts_store import resolve as resolve_prompt
    default = COMPONENT_VALIDATOR_PROMPTS.get(component_type, "당신은 교육 콘텐츠 품질 평가자입니다.\n" + _BASE_OUTPUT_FORMAT)
    return resolve_prompt(f"validator_{component_type}", default)


async def rubric_validate(component_type: str, content: dict, validator_provider: str) -> dict:
    rubric_items = _items_for(component_type)
    if not rubric_items:
        return {"passed": True, "results": [], "overall_score": 100.0}

    system_prompt = _get_validator_prompt(component_type)
    user = (
        f"[컴포넌트 타입]\n{component_type}\n\n"
        f"[루브릭 항목]\n{json.dumps(rubric_items, ensure_ascii=False, indent=2)}\n\n"
        f"[대상 컴포넌트]\n{json.dumps(content, ensure_ascii=False, indent=2)}\n\n"
        "위 루브릭 각 항목에 대해 PASS/MARGINAL/FAIL 판정 JSON을 출력하라."
    )
    resp = await call_model(validator_provider, system_prompt, user, json_mode=True, temperature=0.2, max_tokens=6000)
    resp = resp if isinstance(resp, dict) else {"results": [], "overall_score": 0}
    score = float(resp.get("overall_score") or 0)
    resp["passed"] = score >= RUBRIC_OVERALL_PASS
    return resp


def extract_flags_from_results(component_id: str, run_id: str, component_type: str, results: dict) -> list[dict]:
    """검증 결과 → flags 테이블 insert 대상."""
    rubric = _load_rubric()
    flag_type_map = rubric.get("flag_type_mapping", {})
    fact_ids = set(flag_type_map.get("fact_check_ids") or [])
    consist_ids = set(flag_type_map.get("consistency_ids") or [])
    sensitive_ids = set(flag_type_map.get("sensitive_ids") or [])
    default_type = flag_type_map.get("default", "SCHEMA")

    items_by_id = {item["id"]: item for item in _items_for(component_type)}
    flags: list[dict] = []
    for r in results.get("results", []) or []:
        rid = r.get("id")
        verdict = r.get("verdict")
        evidence = r.get("evidence", "")
        if verdict == "PASS":
            continue
        item = items_by_id.get(rid, {})
        severity = item.get("severity_if_fail", "중")
        if verdict == "MARGINAL":
            ftype = "BORDERLINE"
        elif rid in fact_ids:
            ftype = "FACT"
        elif rid in consist_ids:
            ftype = "CONSISTENCY"
        elif rid in sensitive_ids:
            ftype = "SENSITIVE"
        else:
            ftype = default_type
        flags.append({
            "component_id": component_id,
            "run_id": run_id,
            "flag_type": ftype,
            "severity": severity,
            "location_path": f"{component_type} > {rid}",
            "reason": item.get("description") or rid,
            "guide": f"[{rid}] {evidence}",
            "origin_text": evidence[:500] if evidence else "",
        })
    return flags

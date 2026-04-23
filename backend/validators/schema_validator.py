"""
순수 Python (no LLM) 검증자.
JSON Schema + quiz-types.md의 자동 규칙을 코드로 확인.
"""
from __future__ import annotations
import json
from typing import Any
from jsonschema import Draft7Validator
from ..config import SCHEMA_PATH

_schema_cache = None  # type: ignore


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_cache


def _validator_for(definition_key: str) -> Draft7Validator:
    schema = _load_schema()
    inner = schema["definitions"][definition_key]
    # Draft7Validator에 전체 schema를 넘기되, 특정 definition만 검사 가능하도록 $ref 감싸기
    root = {"$ref": f"#/definitions/{definition_key}", "definitions": schema["definitions"]}
    return Draft7Validator(root)


def validate_component(component_type: str, content: Any) -> dict:
    """
    component_type in {"course_overview","part_intro","material_chapter",
                       "quiz_chapter_set","practice_chapter_set"}
    returns: {"passed": bool, "errors": [{"path": str, "reason": str}]}
    """
    errors: list[dict] = []
    mapping = {
        "course_overview": "course_overview",
        "figure_rationale": "figure_rationale",
        "material": "material_chapter",
        "quiz": "quiz_chapter_set",
        "practice": "practice_chapter_set",
    }
    key = mapping.get(component_type, component_type)
    try:
        v = _validator_for(key)
        for err in sorted(v.iter_errors(content), key=lambda e: list(e.path)):
            errors.append({
                "path": "/".join(str(p) for p in err.path) or "(root)",
                "reason": err.message,
            })
    except KeyError:
        return {"passed": False, "errors": [{"path": "(schema)", "reason": f"unknown component type: {component_type}"}]}

    # 추가: 타입별 specific 자동 규칙
    if component_type == "quiz":
        errors.extend(_quiz_rules(content))
    elif component_type == "practice":
        errors.extend(_practice_rules(content))
    elif component_type == "material":
        errors.extend(_material_rules(content))

    return {"passed": len(errors) == 0, "errors": errors}


def _quiz_rules(content: dict) -> list[dict]:
    errors: list[dict] = []
    items = content.get("items") or []
    if len(items) != 10:
        errors.append({"path": "items", "reason": f"총 문항 10개 필요 (현재 {len(items)})"})
    # 유형별 2개씩
    type_counts: dict[str, int] = {}
    for it in items:
        type_counts[it.get("type", "")] = type_counts.get(it.get("type", ""), 0) + 1
    for t in ["OX", "단일선택", "복수선택", "분류", "단답형"]:
        if type_counts.get(t, 0) != 2:
            errors.append({"path": "items/type", "reason": f"{t} 유형이 정확히 2개여야 함 (현재 {type_counts.get(t,0)})"})
    # 단일선택 검사
    for i, it in enumerate(items):
        tp = it.get("type")
        ans = it.get("answer", "")
        choices = it.get("choices", "")
        if tp == "단일선택":
            if choices.count("(") < 4:
                errors.append({"path": f"items[{i}]/choices", "reason": "단일선택: 보기 4개 필요"})
            if ans.strip() not in ["(1)", "(2)", "(3)", "(4)"]:
                errors.append({"path": f"items[{i}]/answer", "reason": f"단일선택 정답 형식 오류: {ans!r}"})
        elif tp == "복수선택":
            if choices.count("(") < 5:
                errors.append({"path": f"items[{i}]/choices", "reason": "복수선택: 보기 5개 필요"})
            parts = [p.strip() for p in ans.split(",")]
            if len(parts) != 2:
                errors.append({"path": f"items[{i}]/answer", "reason": f"복수선택 정답 정확히 2개 필요: {ans!r}"})
        elif tp == "분류":
            if "/" not in ans:
                errors.append({"path": f"items[{i}]/answer", "reason": "분류 정답은 '[1,3]/[2,4,5]' 형식"})
            else:
                try:
                    left, right = ans.split("/", 1)
                    def parse(s: str) -> list[int]:
                        s = s.strip().strip("[]")
                        return [int(x.strip()) for x in s.split(",") if x.strip()]
                    L, R = parse(left), parse(right)
                    all_ = sorted(L + R)
                    if all_ != [1, 2, 3, 4, 5]:
                        errors.append({"path": f"items[{i}]/answer", "reason": f"분류 그룹 합집합이 {{1..5}}가 아님: {all_}"})
                    if set(L) & set(R):
                        errors.append({"path": f"items[{i}]/answer", "reason": "분류 그룹에 중복 원소 존재"})
                except Exception as e:
                    errors.append({"path": f"items[{i}]/answer", "reason": f"분류 정답 파싱 실패: {e}"})
            cat = (it.get("category") or "").strip()
            if cat.count(",") != 1:
                errors.append({"path": f"items[{i}]/category", "reason": "분류명 2개 (쉼표 1회) 필요"})
        elif tp == "단답형":
            if not any("ㄱ" <= ch <= "ㅎ" for ch in it.get("hint", "")):
                errors.append({"path": f"items[{i}]/hint", "reason": "단답형 힌트에 초성 포함 필요"})
    return errors


def _material_rules(content: dict) -> list[dict]:
    """업로드 분류정리.md 기준 자동 체크 — 표·이모지·고정 소제목·Bad/Good/Better."""
    import re
    errors: list[dict] = []
    sections = content.get("sections") or []
    headings = [s.get("heading", "") for s in sections]
    all_body = "\n".join(s.get("body", "") for s in sections)

    # 1) 필수 소제목 '[ 더 좋은 프롬프트 만들기 ]' 포함 여부
    has_better_heading = any("더 좋은 프롬프트 만들기" in h for h in headings)
    if not has_better_heading:
        errors.append({
            "path": "sections/heading",
            "reason": "소제목 중 하나는 반드시 '[ 더 좋은 프롬프트 만들기 ]' 를 포함해야 함",
        })

    # 2) 소제목 앞에 이모지 아이콘 1개 붙어있는지
    # 간단한 체크: 첫 글자가 BMP 외 플레인(이모지 범위) 또는 '[', '🔁' 등
    emoji_re = re.compile(r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2700-\u27BF\u2600-\u26FF]")
    missing_emoji = [h for h in headings if not (emoji_re.match(h) or h.strip().startswith("["))]
    # 최소 과반 이상은 이모지로 시작해야 함
    if len(sections) >= 3 and len(missing_emoji) > len(sections) // 2:
        errors.append({
            "path": "sections/heading",
            "reason": f"소제목 앞 이모지 아이콘 부족 ({len(missing_emoji)}/{len(sections)} 섹션에서 누락)",
        })

    # 3) Bad/Good/Better 3단 모두 언급되는지 (example 섹션 본문 검사)
    example_section = next((s for s in sections if s.get("kind") == "example"), None)
    if example_section:
        body = example_section.get("body", "")
        missing = [kw for kw in ["Bad", "Good", "Better"] if kw not in body]
        if missing:
            errors.append({
                "path": "sections/example/body",
                "reason": f"Bad/Good/Better 3단 중 누락: {missing}",
            })

    # 4) 마크다운 표 최소 1개 사용 여부
    if "|---" not in all_body and "| ---" not in all_body:
        errors.append({
            "path": "sections/body",
            "reason": "마크다운 표 최소 1개 사용 권장 (비교·분류는 표)",
        })

    # 5) 전체 분량
    total_chars = len(all_body)
    if total_chars < 1500:
        errors.append({"path": "sections", "reason": f"분량 부족: {total_chars}자 (최소 1,500자)"})
    elif total_chars > 3000:
        errors.append({"path": "sections", "reason": f"분량 초과: {total_chars}자 (권장 1,500~2,500자)"})

    # 6) 체크리스트 섹션 항목 수 (5~7)
    reflection_sections = [s for s in sections if s.get("kind") == "reflection"]
    for r in reflection_sections:
        # '체크리스트'가 포함된 제목만
        if "체크리스트" in r.get("heading", ""):
            body = r.get("body", "")
            item_count = body.count("- [ ]") + body.count("- [x]")
            if item_count and not (5 <= item_count <= 7):
                errors.append({
                    "path": "sections/reflection",
                    "reason": f"체크리스트 5~7항목 필요 (현재 {item_count}개)",
                })

    return errors


def _practice_rules(content: dict) -> list[dict]:
    errors: list[dict] = []
    items = content.get("items") or []
    if len(items) != 3:
        errors.append({"path": "items", "reason": f"실습 3개 필요 (현재 {len(items)})"})
    stages_seen = [it.get("stage") for it in items]
    if stages_seen != ["실험", "레슨", "도전"]:
        errors.append({"path": "items/stage", "reason": f"stage 순서는 [실험,레슨,도전]: {stages_seen}"})
    for i, it in enumerate(items):
        # 평가항목 어미·길이 체크
        for j, cri in enumerate(it.get("criteria", []) or []):
            title = cri.get("title", "")
            desc = cri.get("description", "")
            if not title.rstrip().endswith("했나요?"):
                errors.append({"path": f"items[{i}]/criteria[{j}]/title",
                               "reason": f"평가항목 제목은 '~했나요?' 어미: {title!r}"})
            if len(title) > 20:
                errors.append({"path": f"items[{i}]/criteria[{j}]/title",
                               "reason": f"평가항목 제목 최대 20자 (현재 {len(title)}자)"})
            if len(desc) > 40:
                errors.append({"path": f"items[{i}]/criteria[{j}]/description",
                               "reason": f"평가항목 설명 최대 40자 (현재 {len(desc)}자)"})
        # 제목·설명 길이 체크 (업로드 분류정리.md 기준)
        title = it.get("title", "") or ""
        description = it.get("description", "") or ""
        if not (40 <= len(title) <= 100):
            errors.append({"path": f"items[{i}]/title",
                           "reason": f"콘텐츠명 40~100자 (현재 {len(title)}자): {title[:30]!r}"})
        if not (94 <= len(description) <= 140):
            errors.append({"path": f"items[{i}]/description",
                           "reason": f"설명 94~140자 (현재 {len(description)}자)"})
        # 설명에 예시 2개 이상 (간단한 마커 카운트)
        example_markers = sum(description.count(m) for m in ["예)", "예를 들어", "예시)", "1)", "2)", " 또는 "])
        if example_markers < 2:
            errors.append({"path": f"items[{i}]/description",
                           "reason": f"설명에 구체 예시 2개 이상 필요 (발견 마커 {example_markers}개)"})
        # 평가항목 3개 서로 다른 기준 (제목 중복 체크)
        titles = [c.get("title", "") for c in (it.get("criteria", []) or [])]
        if len(set(titles)) < len(titles):
            errors.append({"path": f"items[{i}]/criteria",
                           "reason": "평가항목 3개가 서로 다른 기준이어야 함 (중복 발견)"})
        # 고정값
        for k, v in [("environment", "ChatGPT"), ("response_type", "텍스트"),
                     ("is_free", "FALSE"), ("clip_group_id", "-"), ("file_url", "-")]:
            if it.get(k) != v:
                errors.append({"path": f"items[{i}]/{k}",
                               "reason": f"고정값 불일치: 기대={v!r} 실제={it.get(k)!r}"})
    # 기본 합격점수 50/80/80 (미세 편차 경고만)
    expected_scores = [50, 80, 80]
    actual_scores = [it.get("passing_score") for it in items]
    if actual_scores and actual_scores != expected_scores:
        # 경고 수준으로만 (엄격 차단 X — mixer로 조정 가능하므로)
        errors.append({"path": "items/passing_score",
                       "reason": f"기본 합격점수 50/80/80 권장 (현재 {actual_scores})"})
    return errors

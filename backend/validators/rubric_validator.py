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


SYSTEM = """당신은 교육 콘텐츠 품질 평가자입니다.
입력으로 '루브릭 항목 리스트'와 '대상 컴포넌트(JSON)'를 받아, 각 항목을 PASS / MARGINAL / FAIL 로 판정합니다.

- PASS: 요구조건 충족
- MARGINAL: 애매하게 걸침, 사람 확인 필요
- FAIL: 명백히 미충족

판정 시 '구체적 근거(어느 필드/문장이 왜)'를 evidence에 서술.
출력은 JSON:
{
  "results": [
    {"id": <루브릭 항목 id>, "verdict": "PASS"|"MARGINAL"|"FAIL", "evidence": "..."},
    ...
  ],
  "overall_score": 0~100  -- PASS=1, MARGINAL=0.5, FAIL=0 → 평균×100
}
"""


async def rubric_validate(component_type: str, content: dict, validator_provider: str) -> dict:
    rubric_items = _items_for(component_type)
    if not rubric_items:
        return {"passed": True, "results": [], "overall_score": 100.0}

    user = (
        f"[컴포넌트 타입]\n{component_type}\n\n"
        f"[루브릭 항목]\n{json.dumps(rubric_items, ensure_ascii=False, indent=2)}\n\n"
        f"[대상 컴포넌트]\n{json.dumps(content, ensure_ascii=False, indent=2)}\n\n"
        "판정 JSON을 출력하라."
    )
    resp = await call_model(validator_provider, SYSTEM, user, json_mode=True, temperature=0.2, max_tokens=6000)
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

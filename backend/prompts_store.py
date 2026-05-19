"""
에이전트 시스템 프롬프트 override 저장소.

흐름:
1. 각 agent 파일의 SYSTEM_PROMPT = 코드에 하드코딩된 기본값
2. 관리자가 Admin 페이지에서 프롬프트 수정 → `presets` 테이블에 override 저장
3. agent는 `resolve(name, SYSTEM_PROMPT)` 호출 → override 있으면 그것, 없으면 기본값

override는 즉시 반영 (다음 LLM 호출부터). 코드 재배포 불필요.
"""
from __future__ import annotations
import json
from typing import Optional
from .db import get_conn


# key → (한글 라벨, 카테고리 "generator"|"validator")
AGENT_REGISTRY = {
    # 생성자 7종 (Claude Opus 4.7)
    "course_planner":          ("과정 기획 (Director)", "generator"),
    "figure_rationale":        ("위인 선정 배경",        "generator"),
    "material_writer":         ("학습자료",             "generator"),
    "story_writer":            ("스토리",               "generator"),
    "quiz_generator":          ("퀴즈",                "generator"),
    "practice_generator":      ("실습",                "generator"),
    "special_quiz_generator":  ("특수 퀴즈",            "generator"),
    # 검증자 7종 (GPT-5.4) — 각 컴포넌트 타입별 고유 프롬프트
    "validator_course_overview":  ("과정 기획 검증",      "validator"),
    "validator_figure_rationale": ("위인 선정 배경 검증", "validator"),
    "validator_material":         ("학습자료 검증",       "validator"),
    "validator_story":            ("스토리 검증",        "validator"),
    "validator_quiz":             ("퀴즈 검증",          "validator"),
    "validator_practice":         ("실습 검증",          "validator"),
    "validator_special_quiz":     ("특수 퀴즈 검증",      "validator"),
}


def _preset_key(agent: str) -> str:
    return f"prompt_override_{agent}"


def get_override(agent: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value_json FROM presets WHERE preset_key=?",
            (_preset_key(agent),),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value_json"]).get("text")
    except Exception:
        return None


def get_default(agent: str) -> str:
    """agent의 코드 기본 프롬프트 (override 아님)."""
    if agent.startswith("validator_"):
        ctype = agent.replace("validator_", "")
        # course_overview는 validator 매핑에서 그대로
        from .validators.rubric_validator import COMPONENT_VALIDATOR_PROMPTS
        return COMPONENT_VALIDATOR_PROMPTS.get(ctype, "")
    # generators
    import importlib
    module_map = {
        "course_planner":          "backend.agents.course_planner",
        "figure_rationale":        "backend.agents.figure_rationale",
        "material_writer":         "backend.agents.material_writer",
        "story_writer":            "backend.agents.story_writer",
        "quiz_generator":          "backend.agents.quiz_generator",
        "practice_generator":      "backend.agents.practice_generator",
        "special_quiz_generator":  "backend.agents.special_quiz_generator",
    }
    mod_path = module_map.get(agent)
    if not mod_path:
        return ""
    try:
        mod = importlib.import_module(mod_path)
        return getattr(mod, "SYSTEM_PROMPT", "")
    except Exception:
        return ""


def set_override(agent: str, text: str) -> None:
    if agent not in AGENT_REGISTRY:
        raise ValueError(f"unknown agent: {agent}")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO presets(preset_key, version, value_json) VALUES (?, ?, ?)",
            (_preset_key(agent), "override", json.dumps({"text": text}, ensure_ascii=False)),
        )
        conn.commit()


def clear_override(agent: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM presets WHERE preset_key=?", (_preset_key(agent),))
        conn.commit()


def resolve(agent: str, default: str) -> str:
    """override 있으면 반환, 없으면 default (코드 하드코딩 값)."""
    ov = get_override(agent)
    return ov if ov else default

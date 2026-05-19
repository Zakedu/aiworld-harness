"""
Glossary Validator — data/glossary.yaml 기반 용어 일관성 검증.

validate_content(text, component_type) → list[dict] (위반 항목)
각 위반 항목: {"rule", "message", "severity": "error"|"warn"|"info"}
"""
from __future__ import annotations
import json
import re
import yaml
from functools import lru_cache
from pathlib import Path

_GLOSSARY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "glossary.yaml"


@lru_cache(maxsize=1)
def _load_glossary() -> dict:
    with open(_GLOSSARY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_content(text: str, component_type: str) -> list[dict]:
    """콘텐츠 문자열에서 용어 위반 항목을 탐지해 반환."""
    if not text:
        return []

    g = _load_glossary()
    violations: list[dict] = []

    # ── 1. 금지 단어 체크 ────────────────────────────────
    for term in g.get("terms", []):
        for forbidden in term.get("forbidden", []):
            if not forbidden:
                continue
            if re.search(re.escape(forbidden), text, re.IGNORECASE):
                violations.append({
                    "rule": "terminology",
                    "message": f"금지 표현 '{forbidden}' 감지 → '{term['canonical']}' 사용 권장 (맥락: {term.get('context', '-')})",
                    "severity": "warn",
                })

    # ── 2. 패턴 체크 ────────────────────────────────────
    for pattern in g.get("patterns", []):
        forbidden_in: list[str] = pattern.get("forbidden_in", [])
        if forbidden_in and component_type not in forbidden_in:
            continue
        try:
            if re.search(pattern["regex"], text, re.IGNORECASE | re.UNICODE):
                violations.append({
                    "rule": pattern["name"],
                    "message": pattern["message"],
                    "severity": pattern.get("severity", "warn"),
                })
        except re.error:
            pass  # 잘못된 정규식은 무시

    return violations


def validate_component(component_content: dict, component_type: str) -> list[dict]:
    """컴포넌트 content dict 전체를 JSON 직렬화 후 검증."""
    text = json.dumps(component_content, ensure_ascii=False)
    return validate_content(text, component_type)

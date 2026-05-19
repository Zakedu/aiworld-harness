"""
Generator/Validator가 공통으로 쓰는 LLM 클라이언트 래퍼.

두 프로바이더를 같은 인터페이스(`call_model`)로 추상화하여,
교차검증 매트릭스에서 'claude' | 'openai' 문자열 하나로 스위칭할 수 있게 한다.
"""
from __future__ import annotations
import json
from typing import Any
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from ..config import (
    ANTHROPIC_API_KEY, OPENAI_API_KEY,
    CLAUDE_MODEL, OPENAI_MODEL,
)

_anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
_openai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def call_model(
    provider: str,
    system: str,
    user: str,
    *,
    json_mode: bool = True,
    temperature: float = 0.4,
    max_tokens: int = 12000,
) -> dict[str, Any] | str:
    """Dispatch to the right provider. json_mode=True → 응답을 dict로 파싱."""
    provider = provider.lower()
    if provider == "claude":
        return await _call_claude(system, user, json_mode, temperature, max_tokens)
    elif provider == "openai":
        return await _call_openai(system, user, json_mode, temperature, max_tokens)
    else:
        raise ValueError(f"unknown provider: {provider}")


async def _call_claude(system, user, json_mode, temperature, max_tokens):
    """
    Claude 4.x reasoning 모델(claude-opus-4-7 등)은 temperature deprecated.
    예전 모델(claude-3-x) 호환 위해 모델명에 '3-'이 들어있을 때만 temperature 전달.
    """
    if _anthropic is None:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    kwargs: dict = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system + (_JSON_INSTRUCTION if json_mode else ""),
        "messages": [{"role": "user", "content": user}],
    }
    if "claude-3" in CLAUDE_MODEL:
        kwargs["temperature"] = temperature
    msg = await _anthropic.messages.create(**kwargs)
    text = "".join(block.text for block in msg.content if hasattr(block, "text"))
    return _maybe_parse_json(text) if json_mode else text


async def _call_openai(system, user, json_mode, temperature, max_tokens):
    """
    OpenAI 5.x reasoning 모델도 temperature 미지원 가능성 있음.
    gpt-5, gpt-4o 계열에서는 temperature 기본 허용하나,
    gpt-5.4/o1 등 reasoning 모델은 안 됨. 안전하게 gpt-5/o1은 제외.
    max_tokens도 신모델에선 max_completion_tokens로 변경됨.
    """
    if _openai is None:
        raise RuntimeError("OPENAI_API_KEY not set")
    is_reasoning = any(tag in OPENAI_MODEL for tag in ["gpt-5", "o1", "o3"])
    kwargs: dict = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system + (_JSON_INSTRUCTION if json_mode else "")},
            {"role": "user", "content": user},
        ],
    }
    if is_reasoning:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await _openai.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content or ""
    return _maybe_parse_json(text) if json_mode else text


_JSON_INSTRUCTION = (
    "\n\n[출력 형식] 반드시 단일 JSON 오브젝트만 출력하라. "
    "코드블록(```) 금지. 설명 텍스트 금지. 첫 글자는 '{', 마지막 글자는 '}'."
)


def _maybe_parse_json(text: str) -> dict[str, Any]:
    """코드펜스 제거 후 JSON 파싱. 실패 시 원문을 error 필드에 담아 반환."""
    t = text.strip()
    if t.startswith("```"):
        # 첫 줄(```json)과 마지막 ``` 제거
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        # JSON이 문장 중간에 있을 수도 있으니 첫 { ~ 마지막 } 추출 시도
        s, eidx = t.find("{"), t.rfind("}")
        if s >= 0 and eidx > s:
            try:
                return json.loads(t[s : eidx + 1])
            except Exception:
                pass
        return {"_parse_error": str(e), "_raw": text}

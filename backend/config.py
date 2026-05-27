"""환경 변수 로딩 및 전역 설정."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

# --- API keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Models (user-specified) ---
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

# --- Paths ---
def _resolve(env_key: str, default: str) -> Path:
    val = os.getenv(env_key, default)
    p = Path(val)
    return p if p.is_absolute() else ROOT / val.lstrip("./")

DB_PATH = _resolve("DB_PATH", "data/aiworld.db")
SCHEMA_PATH = _resolve("SCHEMA_PATH", "data/schema-v1.json")
RUBRIC_PATH = _resolve("RUBRIC_PATH", "data/rubric-v1.yaml")
GOLDENS_PATH = _resolve("GOLDENS_PATH", "data/goldens")

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

# --- Runtime ---
MAX_REGEN_RETRIES = int(os.getenv("MAX_REGEN_RETRIES", "3"))
RUBRIC_OVERALL_PASS = int(os.getenv("RUBRIC_OVERALL_PASS", "80"))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "3"))
LLM_TRANSIENT_RETRIES = int(os.getenv("LLM_TRANSIENT_RETRIES", "2"))
RUBRIC_VALIDATION_TIMEOUT_SECONDS = int(os.getenv("RUBRIC_VALIDATION_TIMEOUT_SECONDS", "90"))

# --- Cross-validation matrix (컴포넌트 → (generator, validator)) ---
# v1.1 단순화: 전부 Claude 생성 → GPT-5.4 검증 (명확한 역할 분리)
# 각 컴포넌트의 프롬프트는 타입별로 고유 (생성·검증 모두)
CROSS_MATRIX: dict[str, tuple[str, str]] = {
    "course_overview":   ("claude", "openai"),
    "figure_rationale":  ("claude", "openai"),
    "material":          ("claude", "openai"),
    "story":             ("claude", "openai"),
    "quiz":              ("claude", "openai"),
    "practice":          ("claude", "openai"),
    "special_quiz":      ("claude", "openai"),
}

FRONTEND_DIR = ROOT / "frontend"

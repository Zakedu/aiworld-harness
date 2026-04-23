"""환경 변수 로딩 및 전역 설정."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

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
PORT = int(os.getenv("PORT", "8000"))

# --- Runtime ---
MAX_REGEN_RETRIES = int(os.getenv("MAX_REGEN_RETRIES", "3"))
RUBRIC_OVERALL_PASS = int(os.getenv("RUBRIC_OVERALL_PASS", "80"))

# --- Cross-validation matrix (컴포넌트 → (generator, validator)) ---
# v1.0: 'part_intro'가 'figure_rationale'로 교체됨 (파트별 5개 → 코스당 1개)
CROSS_MATRIX: dict[str, tuple[str, str]] = {
    "course_overview":   ("claude", "openai"),
    "figure_rationale":  ("openai", "claude"),
    "material":          ("claude", "openai"),
    "quiz":              ("openai", "claude"),
    "practice":          ("claude", "openai"),
}

FRONTEND_DIR = ROOT / "frontend"

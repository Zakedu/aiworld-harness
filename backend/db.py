"""SQLite 스키마 정의 + 초기화."""
from __future__ import annotations
import sqlite3
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from .config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
  run_id         TEXT PRIMARY KEY,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status         TEXT,
  inputs_json    TEXT,
  mixer_json     TEXT,
  preset_version TEXT
);

CREATE TABLE IF NOT EXISTS blueprints (
  blueprint_id    TEXT PRIMARY KEY,
  run_id          TEXT REFERENCES runs(run_id),
  version         INTEGER DEFAULT 1,
  content_json    TEXT,
  generator_model TEXT,
  approved_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS components (
  component_id    TEXT PRIMARY KEY,
  run_id          TEXT REFERENCES runs(run_id),
  blueprint_id    TEXT REFERENCES blueprints(blueprint_id),
  type            TEXT,
  chapter_id      TEXT,
  version         INTEGER DEFAULT 1,
  generator_model TEXT,
  validator_model TEXT,
  content_json    TEXT,
  status          TEXT,
  parent_version  INTEGER,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS validations (
  validation_id       TEXT PRIMARY KEY,
  component_id        TEXT REFERENCES components(component_id),
  validator_type      TEXT,
  validator_model     TEXT,
  rubric_results_json TEXT,
  overall_score       REAL,
  passed              INTEGER,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS flags (
  flag_id       TEXT PRIMARY KEY,
  component_id  TEXT REFERENCES components(component_id),
  run_id        TEXT REFERENCES runs(run_id),
  flag_type     TEXT,
  severity      TEXT,
  location_path TEXT,
  reason        TEXT,
  guide         TEXT,
  origin_text   TEXT,
  resolved      INTEGER DEFAULT 0,
  resolution    TEXT,
  resolved_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regenerations (
  regen_id            TEXT PRIMARY KEY,
  source_component_id TEXT REFERENCES components(component_id),
  target_component_id TEXT REFERENCES components(component_id),
  flag_id             TEXT REFERENCES flags(flag_id),
  scope               TEXT,
  user_instruction    TEXT,
  generator_model     TEXT,
  validator_model     TEXT,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS presets (
  preset_key  TEXT PRIMARY KEY,
  version     TEXT,
  value_json  TEXT,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goldens (
  golden_id    TEXT PRIMARY KEY,
  type         TEXT,
  label        TEXT,
  content_json TEXT,
  source_run   TEXT
);

CREATE INDEX IF NOT EXISTS idx_components_run ON components(run_id);
CREATE INDEX IF NOT EXISTS idx_flags_run ON flags(run_id, resolved);
CREATE INDEX IF NOT EXISTS idx_validations_component ON validations(component_id);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def tx():
    """트랜잭션 컨텍스트."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """DB 초기화 + 기본 프리셋 삽입."""
    with tx() as conn:
        conn.executescript(SCHEMA_SQL)
        _seed_presets(conn)
    print(f"[db] initialized at {DB_PATH}")


def _seed_presets(conn: sqlite3.Connection):
    """schema/rubric을 프리셋 테이블에 기록 (버전 추적용)."""
    from .config import SCHEMA_PATH, RUBRIC_PATH
    import yaml  # type: ignore

    # schema
    if SCHEMA_PATH.exists():
        schema_obj = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR REPLACE INTO presets(preset_key, version, value_json) VALUES (?,?,?)",
            ("schema", schema_obj.get("title", "v1.0"), json.dumps(schema_obj, ensure_ascii=False)),
        )
    # rubric
    if RUBRIC_PATH.exists():
        rubric_obj = yaml.safe_load(RUBRIC_PATH.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR REPLACE INTO presets(preset_key, version, value_json) VALUES (?,?,?)",
            ("rubric", rubric_obj.get("version", "1.0"), json.dumps(rubric_obj, ensure_ascii=False)),
        )
    # tone / courseid rule — 하드코드 초기값
    conn.execute(
        "INSERT OR REPLACE INTO presets(preset_key, version, value_json) VALUES (?,?,?)",
        ("tone", "v1.0", json.dumps({"style": "위인 멘토링 시뮬레이션", "figure_voice": True}, ensure_ascii=False)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO presets(preset_key, version, value_json) VALUES (?,?,?)",
        ("courseid_rule", "v1.0", json.dumps({"pattern": "AW-YYYYMMDD-{seq:03d}"}, ensure_ascii=False)),
    )


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "init":
        init_db()
    else:
        print(f"unknown command: {cmd}")

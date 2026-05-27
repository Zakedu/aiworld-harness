"""
AI World Harness — FastAPI entrypoint.

실행: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Any, Optional

from fastapi.responses import StreamingResponse
from urllib.parse import quote

from .config import FRONTEND_DIR, HOST, PORT
from .db import get_conn, init_db
from .ws import ws_manager
from . import orchestrator
from .exporters.xlsx_export import build_xlsx
from .exporters.zip_export import build_zip
from .exporters.sql_export import build_sql
from .prompts_store import AGENT_REGISTRY, get_override, set_override, clear_override, get_default

app = FastAPI(title="AI World Harness", version="1.0")


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class RunCreate(BaseModel):
    figure: str
    topic: str
    target_learner: str
    learning_goals: list[str] = Field(default_factory=list)
    chapters: int = 10                 # total = parts_count × chapters_per_part
    parts_count: int = 5
    chapters_per_part: int = 2
    category: str = "auto"             # "auto" | 업무생산성 | 마케팅 | ...
    chapter_duration_min: int = 15
    mixer: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

@app.on_event("startup")
async def _startup():
    init_db()


# ------------------------------------------------------------------
# REST API
# ------------------------------------------------------------------

@app.post("/api/runs")
async def create_run(body: RunCreate):
    run_id = f"AW-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs(run_id, status, inputs_json, mixer_json, preset_version) VALUES (?,?,?,?,?)",
            (run_id, "planning",
             json.dumps(body.model_dump(exclude={"mixer"}), ensure_ascii=False),
             json.dumps(body.mixer, ensure_ascii=False),
             "v1.0"),
        )
        conn.commit()

    inputs = body.model_dump(exclude={"mixer"})
    _t = asyncio.create_task(orchestrator.run_planning(run_id, inputs, body.mixer))
    _t.add_done_callback(lambda t: orchestrator._task_error_handler(t, run_id))
    return {"run_id": run_id, "status": "planning"}


@app.get("/api/runs")
def list_runs(limit: int = 20):
    """최근 run 목록 — 히스토리·run picker용."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT run_id, created_at, status, inputs_json FROM runs ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["inputs"] = json.loads(d.pop("inputs_json") or "{}")
        except Exception:
            d["inputs"] = {}
        out.append(d)
    return out


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with get_conn() as conn:
        run = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(404, "run not found")
        bp = conn.execute(
            "SELECT blueprint_id, version, content_json, generator_model, approved_at FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        # 최신 버전만 노출 (재생성으로 쌓인 과거 버전 제외)
        comps = conn.execute(
            """
            SELECT c.component_id, c.type, c.chapter_id, c.version, c.status,
                   c.generator_model, c.validator_model
            FROM components c
            INNER JOIN (
                SELECT type, chapter_id, MAX(version) AS maxv
                FROM components WHERE run_id=?
                GROUP BY type, chapter_id
            ) m ON c.type = m.type AND c.chapter_id = m.chapter_id AND c.version = m.maxv
            WHERE c.run_id=?
            ORDER BY c.type, c.chapter_id
            """,
            (run_id, run_id),
        ).fetchall()
        flags = conn.execute(
            "SELECT * FROM flags WHERE run_id=? AND resolved=0",
            (run_id,),
        ).fetchall()
    missing = orchestrator.find_recoverable_components_for_run(run_id)

    return {
        "run": dict(run),
        "blueprint": (dict(bp) | {"content": json.loads(bp["content_json"])}) if bp else None,
        "components": [dict(c) for c in comps],
        "flags": [dict(f) for f in flags],
        "missing_components": missing,
    }


@app.get("/api/runs/{run_id}/summary")
def run_summary(run_id: str):
    """진척·통계 요약 — Screen 2/3의 상단 stats bar용."""
    with get_conn() as conn:
        run = conn.execute("SELECT run_id, status, created_at FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(404, "run not found")
        by_type = conn.execute(
            """SELECT type, status, COUNT(*) AS n FROM components
               WHERE run_id=? GROUP BY type, status""",
            (run_id,),
        ).fetchall()
        flags_total = conn.execute(
            "SELECT COUNT(*) AS n FROM flags WHERE run_id=? AND resolved=0", (run_id,)
        ).fetchone()["n"]
        flags_by_type = conn.execute(
            """SELECT flag_type, COUNT(*) AS n FROM flags
               WHERE run_id=? AND resolved=0 GROUP BY flag_type""",
            (run_id,),
        ).fetchall()
    matrix: dict = {}
    for r in by_type:
        matrix.setdefault(r["type"], {})[r["status"]] = r["n"]
    return {
        "run": dict(run),
        "matrix": matrix,
        "flags_total": flags_total,
        "flags_by_type": {r["flag_type"]: r["n"] for r in flags_by_type},
    }


@app.post("/api/runs/{run_id}/approve-blueprint")
async def approve(run_id: str, body: dict):
    # 사용자가 수정한 content가 있으면 DB에 반영
    edited = body.get("content")
    if edited:
        with get_conn() as conn:
            conn.execute(
                "UPDATE blueprints SET content_json=? WHERE blueprint_id=?",
                (json.dumps(edited, ensure_ascii=False), body["blueprint_id"]),
            )
            conn.commit()
    await orchestrator.approve_blueprint(run_id, body["blueprint_id"])
    return {"ok": True}


@app.get("/api/components/{component_id}")
def get_component(component_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM components WHERE component_id=?", (component_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        flags = conn.execute(
            "SELECT * FROM flags WHERE component_id=? AND resolved=0 ORDER BY severity DESC, flag_type",
            (component_id,),
        ).fetchall()
        validations = conn.execute(
            "SELECT * FROM validations WHERE component_id=? ORDER BY created_at DESC LIMIT 1",
            (component_id,),
        ).fetchone()
    d = dict(row)
    d["content"] = json.loads(d["content_json"])
    d.pop("content_json", None)
    d["flags"] = [dict(f) for f in flags]
    if validations:
        v = dict(validations)
        try:
            v["rubric_results"] = json.loads(v.pop("rubric_results_json") or "{}")
        except Exception:
            v["rubric_results"] = {}
        d["latest_validation"] = v
    return d


@app.get("/api/runs/{run_id}/export.xlsx")
def export_xlsx(run_id: str):
    """비개발자용 — 내용 중심 (SQL 컬럼 없음)."""
    try:
        filename, data = build_xlsx(run_id, mode="user")
    except ValueError as e:
        raise HTTPException(404, str(e))
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/api/runs/{run_id}/export.dev.xlsx")
def export_xlsx_dev(run_id: str):
    """개발자용 — SQL 컬럼·설정·course_practice_quiz 탭."""
    try:
        filename, data = build_xlsx(run_id, mode="dev")
    except ValueError as e:
        raise HTTPException(404, str(e))
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.post("/api/runs/{run_id}/revalidate")
async def revalidate_run(run_id: str):
    """generated/validation_error 컴포넌트 일괄 재검증."""
    with get_conn() as conn:
        row = conn.execute("SELECT run_id FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "run not found")
    _t = asyncio.create_task(orchestrator.revalidate_run(run_id))
    _t.add_done_callback(lambda t: orchestrator._task_error_handler(t, run_id))
    return {"status": "revalidation_started", "run_id": run_id}


class RecoverRunBody(BaseModel):
    components: list[str] = Field(default_factory=lambda: ["quiz", "practice"])
    include_failed: bool = True


@app.post("/api/runs/{run_id}/recover-components")
async def recover_components(run_id: str, body: RecoverRunBody):
    """누락되었거나 validator 오류가 난 컴포넌트를 다시 생성."""
    allowed = {"material", "story", "quiz", "practice"}
    comps = tuple(c for c in body.components if c in allowed) or ("quiz", "practice")
    with get_conn() as conn:
        row = conn.execute("SELECT run_id FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "run not found")
    _t = asyncio.create_task(orchestrator.recover_run_components(run_id, comps, body.include_failed))
    _t.add_done_callback(lambda t: orchestrator._task_error_handler(t, run_id))
    return {
        "status": "recovery_started",
        "run_id": run_id,
        "components": comps,
        "include_failed": body.include_failed,
    }


@app.get("/api/runs/{run_id}/export.sql")
def export_sql(run_id: str):
    """INSERT SQL 파일 다운로드 — quiz / practice / course_practice_quiz 3개 테이블."""
    try:
        filename, sql_text = build_sql(run_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(
        iter([sql_text.encode("utf-8")]),
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )


@app.get("/api/runs/{run_id}/export.zip")
def export_zip(run_id: str):
    """(선택) xlsx + 학습자료 10개 docx 번들 zip. UI 기본은 xlsx 단독."""
    try:
        filename, data = build_zip(run_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return StreamingResponse(iter([data]), media_type="application/zip", headers=headers)


@app.get("/api/components/{component_id}/export.docx")
def export_component_docx(component_id: str):
    """단일 학습자료 컴포넌트를 docx로 다운로드 (Review pane의 개별 다운로드 버튼)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT c.*, b.content_json AS bp_json FROM components c "
            "LEFT JOIN blueprints b ON b.blueprint_id = c.blueprint_id "
            "WHERE c.component_id=?",
            (component_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "component not found")
    if row["type"] != "material":
        raise HTTPException(400, "docx export is available for material components only")
    from .exporters.docx_export import build_material_docx
    bp = json.loads(row["bp_json"] or "{}")
    course_name = bp.get("course_name", "AI World Course")
    chap_id = row["chapter_id"]
    chap_name = next((c["chapter_name"] for c in (bp.get("curriculum") or []) if c.get("chapter_id") == chap_id), "")
    content = json.loads(row["content_json"] or "{}")
    data = build_material_docx(course_name, chap_id, chap_name, content)
    safe = (chap_name or "material").replace("/", "_").replace("\\", "_")[:60]
    filename = f"[AW] {chap_id}_{safe}.docx"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@app.get("/api/runs/{run_id}/chapters/{chapter_id}/material.html",
         response_class=HTMLResponse)
def export_material_html(run_id: str, chapter_id: str):
    """챕터 학습자료를 프리미엄 HTML로 반환 (브라우저에서 직접 열기 / PDF 저장)."""
    from .exporters.html_export import build_material_html
    try:
        html_content = build_material_html(run_id, chapter_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return HTMLResponse(content=html_content)


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    """Run과 그에 딸린 모든 레코드를 삭제 (cascade)."""
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "run not found")
        # FK cascade가 걸려있지 않으므로 수동으로 정리
        conn.execute("DELETE FROM regenerations WHERE source_component_id IN (SELECT component_id FROM components WHERE run_id=?) OR target_component_id IN (SELECT component_id FROM components WHERE run_id=?)", (run_id, run_id))
        conn.execute("DELETE FROM validations WHERE component_id IN (SELECT component_id FROM components WHERE run_id=?)", (run_id,))
        conn.execute("DELETE FROM flags WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM components WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM blueprints WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        conn.commit()
    return {"ok": True, "run_id": run_id}


class ChapterRegenBody(BaseModel):
    instruction: str = ""
    components: list[str] = Field(default_factory=list)  # ["material","quiz","practice"] — 빈 리스트면 전체


@app.post("/api/runs/{run_id}/chapters/{chapter_id}/regenerate")
async def chapter_regenerate(run_id: str, chapter_id: str, body: ChapterRegenBody):
    """챕터 1개의 학습자료·퀴즈·실습을 사용자 피드백과 함께 재생성."""
    comps = body.components or ["material", "quiz", "practice"]
    _t = asyncio.create_task(orchestrator.regenerate_chapter(run_id, chapter_id, body.instruction, comps))
    _t.add_done_callback(lambda t: orchestrator._task_error_handler(t, run_id))
    return {"ok": True, "chapter_id": chapter_id, "components": comps}


class BulkResolveBody(BaseModel):
    flag_ids: list[str]
    resolution: str = "dismissed"


@app.post("/api/flags/bulk-resolve")
def bulk_resolve(body: BulkResolveBody):
    if not body.flag_ids:
        return {"ok": True, "count": 0}
    placeholders = ",".join("?" * len(body.flag_ids))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE flags SET resolved=1, resolution=?, resolved_at=CURRENT_TIMESTAMP WHERE flag_id IN ({placeholders})",
            [body.resolution] + list(body.flag_ids),
        )
        conn.commit()
    return {"ok": True, "count": len(body.flag_ids)}


class RegenBody(BaseModel):
    item_index: int
    instruction: str
    flag_id: Optional[str] = None


@app.post("/api/components/{component_id}/regenerate-item")
async def regen_item(component_id: str, body: RegenBody):
    result = await orchestrator.regenerate_item(
        component_id, body.item_index, body.instruction, body.flag_id
    )
    return result


class FlagResolve(BaseModel):
    resolution: str       # "inline_edited" | "dismissed" | "approved"
    new_text: Optional[str] = None


@app.post("/api/flags/{flag_id}/resolve")
def resolve_flag(flag_id: str, body: FlagResolve):
    with get_conn() as conn:
        conn.execute(
            "UPDATE flags SET resolved=1, resolution=?, resolved_at=CURRENT_TIMESTAMP WHERE flag_id=?",
            (body.resolution, flag_id),
        )
        conn.commit()
    return {"ok": True}


# ============================================================
# Admin — 환경설정 · 프롬프트 열람/수정
# ============================================================

@app.get("/api/admin/config")
def admin_config():
    """환경설정 요약 (API 키는 마스킹). 수정은 불가, 열람만."""
    from .config import (
        ANTHROPIC_API_KEY, OPENAI_API_KEY, CLAUDE_MODEL, OPENAI_MODEL,
        CROSS_MATRIX, MAX_REGEN_RETRIES, RUBRIC_OVERALL_PASS,
        LLM_MAX_CONCURRENCY, LLM_TRANSIENT_RETRIES, RUBRIC_VALIDATION_TIMEOUT_SECONDS,
        HOST, PORT,
    )
    def mask(k: str) -> str:
        if not k:
            return "(not set)"
        if len(k) <= 14:
            return "***"
        return f"{k[:10]}…{k[-4:]}"
    return {
        "models": {"claude": CLAUDE_MODEL, "openai": OPENAI_MODEL},
        "api_keys": {
            "anthropic": mask(ANTHROPIC_API_KEY),
            "openai": mask(OPENAI_API_KEY),
        },
        "cross_matrix": {k: list(v) for k, v in CROSS_MATRIX.items()},
        "retry_limit": MAX_REGEN_RETRIES,
        "llm_max_concurrency": LLM_MAX_CONCURRENCY,
        "llm_transient_retries": LLM_TRANSIENT_RETRIES,
        "rubric_validation_timeout_seconds": RUBRIC_VALIDATION_TIMEOUT_SECONDS,
        "overall_pass": RUBRIC_OVERALL_PASS,
        "server": {"host": HOST, "port": PORT},
    }


@app.post("/api/admin/api-key")
async def update_api_key(body: dict):
    """API 키를 .env 파일에 업데이트."""
    import re
    from .config import ROOT
    key_name = body.get("key")   # "OPENAI_API_KEY" | "ANTHROPIC_API_KEY"
    key_value = body.get("value", "").strip()
    allowed = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY"}
    if key_name not in allowed:
        raise HTTPException(400, "허용되지 않은 키 이름")
    if not key_value:
        raise HTTPException(400, "키 값이 비어있습니다")

    env_path = ROOT / ".env"
    if not env_path.exists():
        raise HTTPException(500, ".env 파일을 찾을 수 없습니다")

    text = env_path.read_text()
    pattern = rf"^{key_name}=.*$"
    new_line = f"{key_name}={key_value}"
    if re.search(pattern, text, re.MULTILINE):
        text = re.sub(pattern, new_line, text, flags=re.MULTILINE)
    else:
        text = text.rstrip("\n") + f"\n{new_line}\n"
    env_path.write_text(text)

    # 실행 중인 서버에 즉시 반영 (재시작 불필요)
    import os as _os
    _os.environ[key_name] = key_value
    import backend.config as _cfg
    import backend.agents.base as _base
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI
    if key_name == "ANTHROPIC_API_KEY":
        _cfg.ANTHROPIC_API_KEY = key_value
        _base._anthropic = AsyncAnthropic(api_key=key_value)
    else:
        _cfg.OPENAI_API_KEY = key_value
        _base._openai = AsyncOpenAI(api_key=key_value)

    return {"status": "ok", "key": key_name}


@app.get("/api/admin/prompts")
def admin_prompts_list():
    """생성자 5 + 검증자 5 = 총 10개 에이전트 시스템 프롬프트 현재 상태."""
    result = []
    for key, (label, category) in AGENT_REGISTRY.items():
        default = get_default(key)
        override = get_override(key)
        result.append({
            "key": key,
            "label": label,
            "category": category,  # "generator" | "validator"
            "default": default,
            "override": override,
            "effective": override or default,
            "is_overridden": bool(override),
            "default_length": len(default),
            "effective_length": len(override or default),
        })
    return result


class PromptOverrideBody(BaseModel):
    text: str


@app.put("/api/admin/prompts/{agent}")
def admin_prompts_save(agent: str, body: PromptOverrideBody):
    if agent not in AGENT_REGISTRY:
        raise HTTPException(404, f"unknown agent: {agent}")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "프롬프트 내용이 비어있습니다")
    set_override(agent, text)
    return {"ok": True, "agent": agent, "length": len(text)}


@app.delete("/api/admin/prompts/{agent}")
def admin_prompts_reset(agent: str):
    if agent not in AGENT_REGISTRY:
        raise HTTPException(404)
    clear_override(agent)
    return {"ok": True, "agent": agent}


@app.get("/api/presets/{key}")
def get_preset(key: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM presets WHERE preset_key=?", (key,)).fetchone()
        if not row:
            raise HTTPException(404)
    return dict(row)


# ------------------------------------------------------------------
# WebSocket
# ------------------------------------------------------------------

@app.websocket("/ws/runs/{run_id}")
async def ws_run(ws: WebSocket, run_id: str):
    await ws_manager.connect(run_id, ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive pings
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, ws)


# ------------------------------------------------------------------
# Frontend static serving
# ------------------------------------------------------------------

if FRONTEND_DIR.exists():
    @app.get("/", response_class=HTMLResponse)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

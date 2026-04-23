"""
xlsx + 챕터별 학습자료 docx 들을 zip으로 묶어 한 번에 내려줌.

구조:
  {코스명}_{시각}.zip
    ├── {코스명}.xlsx              (설정/개요/커리큘럼/위인선정배경/퀴즈/실습)
    └── 학습자료/
         ├── 1-1_{챕터명}.docx
         ├── 1-2_{챕터명}.docx
         └── ...
"""
from __future__ import annotations
import io
import json
import zipfile
from datetime import datetime
from .xlsx_export import build_xlsx
from .docx_export import build_material_docx
from ..db import get_conn


def _safe(name: str) -> str:
    bad = '<>:"/\\|?*'
    for c in bad:
        name = name.replace(c, "_")
    return name.strip()[:80] or "file"


def build_zip(run_id: str) -> tuple[str, bytes]:
    """run을 zip으로 패키지. (filename, bytes)"""
    xlsx_name, xlsx_bytes = build_xlsx(run_id)

    # 블루프린트 + material 컴포넌트들 로드
    with get_conn() as conn:
        bp = conn.execute(
            "SELECT content_json FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        materials = conn.execute(
            """
            SELECT c.chapter_id, c.content_json
            FROM components c
            INNER JOIN (
                SELECT chapter_id, MAX(version) AS maxv
                FROM components WHERE run_id=? AND type='material'
                GROUP BY chapter_id
            ) m ON c.chapter_id=m.chapter_id AND c.version=m.maxv
            WHERE c.run_id=? AND c.type='material'
            """,
            (run_id, run_id),
        ).fetchall()

    blueprint = json.loads(bp["content_json"]) if bp else {}
    course_name = blueprint.get("course_name") or run_id
    chapter_names = {c["chapter_id"]: c["chapter_name"] for c in (blueprint.get("curriculum") or [])}

    # Zip 구성
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        # xlsx는 zip 안에서도 그대로 (단 _build_material_tab에서 출력한 학습자료 탭은 xlsx에 유지됨 — 혼동 방지 위해 파일명만 명확히)
        z.writestr(_safe(course_name) + ".xlsx", xlsx_bytes)
        # material docx들
        for mat in materials:
            chap_id = mat["chapter_id"]
            try:
                content = json.loads(mat["content_json"])
            except Exception:
                continue
            name = chapter_names.get(chap_id, "")
            docx_bytes = build_material_docx(course_name, chap_id, name, content)
            fname = f"학습자료/{chap_id}_{_safe(name)}.docx"
            z.writestr(fname, docx_bytes)

    mem.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"[AW] {_safe(course_name)}_{ts}.zip"
    return filename, mem.getvalue()

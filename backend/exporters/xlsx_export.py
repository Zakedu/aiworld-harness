"""
Run 결과물을 aiworld-main BestPractice 템플릿 구조로 xlsx 내보내기.

탭: 설정 / 개요 / 커리큘럼 / 파트 인트로(위인 선정 배경 1개) / 퀴즈(12열) / 실습(18열)
"""
from __future__ import annotations
import io
import json
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from ..db import get_conn


HEADER_FILL = PatternFill(start_color="F4F4F5", end_color="F4F4F5", fill_type="solid")
HEADER_FONT = Font(name="맑은 고딕", bold=True, size=11, color="18181B")
BODY_FONT = Font(name="맑은 고딕", size=10, color="27272A")
THIN = Side(style="thin", color="E4E4E7")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _style_header(ws, row: int, ncols: int):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = BOX
    ws.row_dimensions[row].height = 26


def _style_body(ws, r0: int, r1: int, ncols: int):
    for r in range(r0, r1 + 1):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY_FONT
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BOX
        ws.row_dimensions[r].height = 28


def _set_widths(ws, widths: list[float]):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)].width = w


def build_xlsx(run_id: str) -> tuple[str, bytes]:
    """Run 하나를 xlsx 바이트로 반환. (filename, bytes)"""
    with get_conn() as conn:
        run = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ValueError(f"run not found: {run_id}")
        bp = conn.execute(
            "SELECT content_json FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        # 최신 버전만 추출
        comps = conn.execute(
            """
            SELECT c.type, c.chapter_id, c.content_json, c.version
            FROM components c
            INNER JOIN (
                SELECT type, chapter_id, MAX(version) AS maxv
                FROM components WHERE run_id=?
                GROUP BY type, chapter_id
            ) m ON c.type=m.type AND c.chapter_id=m.chapter_id AND c.version=m.maxv
            WHERE c.run_id=?
            """,
            (run_id, run_id),
        ).fetchall()

    blueprint = json.loads(bp["content_json"]) if bp else {}
    by_key: dict[tuple[str, str], dict] = {}
    for c in comps:
        by_key[(c["type"], c["chapter_id"])] = json.loads(c["content_json"])

    wb = Workbook()
    ws0 = wb.active
    wb.remove(ws0)  # recreate

    _build_settings_tab(wb, run_id)
    _build_overview_tab(wb, blueprint)
    _build_curriculum_tab(wb, blueprint)
    _build_figure_rationale_tab(wb, by_key.get(("figure_rationale", "-")))
    _build_quiz_tab(wb, blueprint, by_key)
    _build_practice_tab(wb, blueprint, by_key)
    _build_material_tab(wb, blueprint, by_key)  # 학습자료 요약 탭 유지 (필요 시 개별 docx 다운로드는 Review에서)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_name = (blueprint.get("course_name") or run_id).replace("/", "_").replace("\\", "_")[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"[AW] {safe_name}_{ts}.xlsx"
    return filename, buf.getvalue()


# ---- Tabs ----

def _build_settings_tab(wb, run_id: str):
    ws = wb.create_sheet("설정")
    ws.append(["항목", "값", "비고"])
    _style_header(ws, 1, 3)
    rows = [
        ("course_id", "", "개발팀 세팅"),
        ("quiz_start_id", "", "개발팀 세팅"),
        ("practice_start_id", "", "개발팀 세팅"),
        ("run_id", run_id, "AI World Harness"),
        ("exported_at", datetime.now().strftime("%Y-%m-%d %H:%M"), ""),
    ]
    for r in rows:
        ws.append(r)
    _style_body(ws, 2, 1 + len(rows), 3)
    _set_widths(ws, [22, 48, 28])


def _build_overview_tab(wb, bp: dict):
    ws = wb.create_sheet("개요")
    ws.append(["항목", "값"])
    _style_header(ws, 1, 2)
    items = [
        ("코스명", bp.get("course_name", "")),
        ("카테고리", bp.get("category", "")),
        ("캐릭터명", bp.get("character_name", "")),
        ("팔릴이유한줄", bp.get("sell_reason", "")),
        ("프로젝트결과물", bp.get("project_outcome", "")),
    ]
    for k, v in items:
        ws.append([k, v])
    t = bp.get("targets") or []
    e = bp.get("effects") or []
    for i in range(3):
        ws.append([f"수강대상{i+1}", t[i] if i < len(t) else ""])
    for i in range(3):
        ws.append([f"수강효과{i+1}", e[i] if i < len(e) else ""])
    _style_body(ws, 2, 1 + 5 + 6, 2)
    _set_widths(ws, [20, 90])


def _build_curriculum_tab(wb, bp: dict):
    ws = wb.create_sheet("커리큘럼")
    ws.append(["구분", "파트", "챕터", "학습자료", "프롬프트 기법", "Drive링크", "진행여부"])
    _style_header(ws, 1, 7)
    for row in bp.get("curriculum", []) or []:
        ws.append([
            row.get("chapter_id", ""),
            row.get("part_name", ""),
            row.get("chapter_name", ""),
            row.get("material_url", "") or "",
            row.get("prompt_technique", ""),
            row.get("drive_url", "") or "",
            str(row.get("done", False)).lower(),
        ])
    _style_body(ws, 2, 1 + len(bp.get("curriculum", []) or []), 7)
    _set_widths(ws, [10, 26, 44, 40, 22, 40, 12])


def _build_figure_rationale_tab(wb, fr: dict | None):
    ws = wb.create_sheet("위인 선정 배경")
    ws.append(["항목", "값"])
    _style_header(ws, 1, 2)
    if not fr:
        ws.append(["—", "데이터 없음"])
        _style_body(ws, 2, 2, 2)
        _set_widths(ws, [20, 90])
        return
    rows = [
        ("위인명", fr.get("figure_name", "")),
        ("오프닝 한 줄", fr.get("opening_one_liner", "")),
        ("배경", fr.get("figure_background", "")),
        ("핵심 철학", fr.get("core_philosophy", "")),
        ("주제 적합성", fr.get("topic_fit_reason", "")),
    ]
    for k, v in rows:
        ws.append([k, v])
    for i, item in enumerate(fr.get("what_learner_gets", []) or [], start=1):
        ws.append([f"학습자 획득{i}", item])
    for i, ep in enumerate(fr.get("key_episodes", []) or [], start=1):
        ws.append([f"에피소드{i} 제목", ep.get("title", "")])
        ws.append([f"에피소드{i} 설명", ep.get("description", "")])
        ws.append([f"에피소드{i} 출처", ep.get("source", "")])
    last = ws.max_row
    _style_body(ws, 2, last, 2)
    _set_widths(ws, [20, 100])


def _build_quiz_tab(wb, bp: dict, by_key: dict):
    ws = wb.create_sheet("퀴즈")
    headers = ["챕터 구분", "clip_group_id", "is_free", "문제 유형", "난이도",
               "제목", "문제", "힌트", "답안 보기", "정답", "분류명", "답안해설"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))
    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id")
        quiz_set = by_key.get(("quiz", chap))
        if not quiz_set:
            continue
        for it in quiz_set.get("items", []) or []:
            ws.append([
                it.get("chapter_id", chap),
                it.get("clip_group_id", "-"),
                it.get("is_free", "TRUE"),
                it.get("type", ""),
                it.get("difficulty", ""),
                it.get("title", ""),
                it.get("question", ""),
                it.get("hint", ""),
                it.get("choices", "-"),
                it.get("answer", ""),
                it.get("category", "-"),
                it.get("explanation", ""),
            ])
    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    _set_widths(ws, [10, 14, 10, 12, 10, 30, 40, 35, 35, 18, 22, 55])


def _build_practice_tab(wb, bp: dict, by_key: dict):
    ws = wb.create_sheet("실습")
    headers = ["챕터 구분", "clip_group_id", "is_free", "콘텐츠명", "문제", "설명",
               "파일URL", "실습환경", "난이도", "정답", "합격점수", "응답형식",
               "평가항목1", "평가항목1-설명", "평가항목2", "평가항목2-설명", "평가항목3", "평가항목3-설명"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))
    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id")
        pset = by_key.get(("practice", chap))
        if not pset:
            continue
        for it in pset.get("items", []) or []:
            crs = it.get("criteria", []) or []
            def _c(i, k):
                return crs[i].get(k, "") if i < len(crs) else ""
            ws.append([
                it.get("chapter_id", chap),
                it.get("clip_group_id", "-"),
                it.get("is_free", "FALSE"),
                it.get("title", ""),
                it.get("question", ""),
                it.get("description", ""),
                it.get("file_url", "-"),
                it.get("environment", "ChatGPT"),
                it.get("difficulty", ""),
                it.get("answer", ""),
                it.get("passing_score", ""),
                it.get("response_type", "텍스트"),
                _c(0, "title"), _c(0, "description"),
                _c(1, "title"), _c(1, "description"),
                _c(2, "title"), _c(2, "description"),
            ])
    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    _set_widths(ws, [10, 14, 10, 28, 40, 32, 12, 14, 10, 55, 12, 12,
                    24, 34, 24, 34, 24, 34])


def _build_material_tab(wb, bp: dict, by_key: dict):
    """학습자료는 Google Docs 대체로 xlsx 한 탭에 텍스트 섹션으로 저장."""
    ws = wb.create_sheet("학습자료")
    ws.append(["챕터", "섹션 제목", "섹션 종류", "본문"])
    _style_header(ws, 1, 4)
    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id")
        mat = by_key.get(("material", chap))
        if not mat:
            continue
        for s in mat.get("sections", []) or []:
            ws.append([chap, s.get("heading", ""), s.get("kind", ""), s.get("body", "")])
    last = ws.max_row
    _style_body(ws, 2, last, 4)
    _set_widths(ws, [10, 30, 16, 100])

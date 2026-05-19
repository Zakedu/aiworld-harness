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


# ---- SQL 변환 유틸 ----

_QUIZ_TYPE_SQL = {
    "OX": "OX",
    "단일선택": "SINGLE",
    "복수선택": "MULTIPLE",
    "분류": "MATCH",
    "단답형": "INPUT",
}

def _to_sql_type(t: str) -> str:
    return _QUIZ_TYPE_SQL.get(t, t)


def _to_answer_json(q_type: str, answer: str, choices: str) -> str:
    """harness answer 포맷 → SQL answer JSON 문자열"""
    import re
    t = _to_sql_type(q_type)

    if t == "OX":
        return json.dumps([{"id": 1, "answer": answer}], ensure_ascii=False)

    if t == "SINGLE":
        # "(2)" → id=2
        m = re.search(r'\((\d+)\)', answer)
        idx = int(m.group(1)) if m else 1
        # choices에서 해당 보기 텍스트 추출
        lines = [l.strip() for l in choices.split('\n') if l.strip()]
        text = ""
        for line in lines:
            lm = re.match(r'^\((\d+)\)\s*(.*)', line)
            if lm and int(lm.group(1)) == idx:
                text = lm.group(2)
                break
        return json.dumps([{"id": idx, "answer": text}], ensure_ascii=False)

    if t == "MULTIPLE":
        # "(1), (3)" → [1, 3]
        ids = [int(x) for x in re.findall(r'\((\d+)\)', answer)]
        lines = [l.strip() for l in choices.split('\n') if l.strip()]
        choice_map = {}
        for line in lines:
            lm = re.match(r'^\((\d+)\)\s*(.*)', line)
            if lm:
                choice_map[int(lm.group(1))] = lm.group(2)
        result = [{"id": i, "answer": choice_map.get(i, "")} for i in ids]
        return json.dumps(result, ensure_ascii=False)

    if t == "MATCH":
        # "[1,3,5]/[2,4]" → [[1,3,5],[2,4]]
        parts = answer.split('/')
        groups = []
        for p in parts:
            nums = [int(x) for x in re.findall(r'\d+', p)]
            groups.append(nums)
        return json.dumps(groups, ensure_ascii=False)

    if t == "INPUT":
        return json.dumps([{"id": 1, "answer": answer}], ensure_ascii=False)

    return json.dumps([{"id": 1, "answer": answer}], ensure_ascii=False)


def _to_answer_options_json(choices: str) -> str:
    """choices 문자열 → SQL answer_options JSON"""
    import re
    if not choices or choices.strip() == "-":
        return "[]"
    lines = [l.strip() for l in choices.split('\n') if l.strip()]
    result = []
    for line in lines:
        m = re.match(r'^\((\d+)\)\s*(.*)', line)
        if m:
            result.append({"id": int(m.group(1)), "answer": m.group(2)})
    return json.dumps(result, ensure_ascii=False)


def _to_match_extras_json(category: str) -> str:
    """분류형 category → SQL extras.matchBuckets JSON"""
    if not category or category.strip() == "-":
        return "{}"
    parts = [p.strip() for p in category.split(',')]
    buckets = [{"bucketName": p, "bucketSequence": i+1} for i, p in enumerate(parts)]
    return json.dumps({"matchBuckets": buckets}, ensure_ascii=False)


def _practice_role(stage: str) -> str:
    """실험 → BAD, 레슨/도전 → GOOD"""
    return "BAD" if stage == "실험" else "GOOD"


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


def build_xlsx(run_id: str, mode: str = "user") -> tuple[str, bytes]:
    """
    Run 하나를 xlsx 바이트로 반환. (filename, bytes)

    mode="user" (기본): 비개발자용 — 내용 중심, SQL 컬럼 없음
    mode="dev":          개발자용 — SQL 컬럼·설정·course_practice_quiz 탭만
    """
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
    wb.remove(ws0)

    if mode == "user":
        _build_overview_tab(wb, blueprint)
        _build_curriculum_tab(wb, blueprint)
        _build_figure_rationale_tab(wb, by_key.get(("figure_rationale", "-")))
        _build_story_tab(wb, blueprint, by_key)
        _build_quiz_tab(wb, blueprint, by_key, sql_cols=False)
        _build_special_quiz_tab(wb, by_key, sql_cols=False)
        _build_practice_tab(wb, blueprint, by_key, sql_cols=False)
        _build_material_tab(wb, blueprint, by_key)
    else:
        _build_settings_tab(wb, run_id)
        _build_quiz_tab(wb, blueprint, by_key, sql_cols=True)
        _build_special_quiz_tab(wb, by_key, sql_cols=True)
        _build_practice_tab(wb, blueprint, by_key, sql_cols=True)
        _build_course_practice_quiz_tab(wb, blueprint, by_key, run_id)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_name = (blueprint.get("course_name") or run_id).replace("/", "_").replace("\\", "_")[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = "" if mode == "user" else "_dev"
    filename = f"[AW] {safe_name}_{ts}{suffix}.xlsx"
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
        ws.cell(row=ws.max_row, column=1).number_format = "@"
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


def _build_quiz_tab(wb, bp: dict, by_key: dict, sql_cols: bool = False):
    ws = wb.create_sheet("퀴즈")
    if sql_cols:
        headers = ["챕터 구분", "clip_group_id", "is_free", "문제 유형",
                   "type_sql", "answer_json", "answer_options_json", "extras_json"]
    else:
        # 제임스 본드 레퍼런스 기준 12열 형태
        headers = ["챕터 구분", "clip_group_id", "is_free", "문제 유형",
                   "난이도", "제목", "문제", "힌트", "답안 보기", "정답", "분류명", "답안해설"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))
    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id")
        quiz_set = by_key.get(("quiz", chap))
        if not quiz_set:
            continue
        for it in quiz_set.get("items", []) or []:
            q_type = it.get("type", "")
            choices = it.get("choices", "-")
            answer = it.get("answer", "")
            category = it.get("category", "-")
            if sql_cols:
                row_data = [
                    it.get("chapter_id", chap),
                    it.get("clip_group_id", "-"),
                    it.get("is_free", "TRUE"),
                    q_type,
                    _to_sql_type(q_type),
                    _to_answer_json(q_type, answer, choices),
                    _to_answer_options_json(choices),
                    _to_match_extras_json(category) if q_type == "분류" else "{}",
                ]
            else:
                row_data = [
                    it.get("chapter_id", chap),
                    it.get("clip_group_id", "-"),
                    it.get("is_free", "TRUE"),
                    q_type,
                    it.get("difficulty", ""),
                    it.get("title", ""),
                    it.get("question", ""),
                    it.get("hint", ""),
                    choices,
                    answer,
                    category,
                    it.get("explanation", ""),
                ]
            ws.append(row_data)
            ws.cell(row=ws.max_row, column=1).number_format = "@"
    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    if sql_cols:
        _set_widths(ws, [10, 14, 10, 12, 10, 50, 50, 40])
    else:
        _set_widths(ws, [10, 14, 8, 12, 10, 30, 40, 35, 35, 18, 22, 55])


_SPECIAL_QUIZ_ROLE_LABEL = {
    "teaser": "파트 티저",
    "part_summary": "파트 종합",
    "final_review": "최종 회고",
}
_SPECIAL_QUIZ_ROLE_ORDER = {"teaser": 0, "part_summary": 1, "final_review": 2}


def _build_special_quiz_tab(wb, by_key: dict, sql_cols: bool = False):
    """파트 티저 / 파트 종합 / 최종 회고."""
    ws = wb.create_sheet("특수 퀴즈")
    if sql_cols:
        headers = ["역할", "파트", "챕터 구분", "clip_group_id", "is_free", "문제 유형",
                   "type_sql", "answer_json", "answer_options_json", "extras_json"]
    else:
        headers = ["역할", "파트", "챕터 구분", "문제 유형", "난이도",
                   "제목", "문제", "힌트", "답안 보기", "정답", "분류명", "답안해설"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))

    sq_entries = [(k, v) for k, v in by_key.items() if k[0] == "special_quiz"]
    sq_entries.sort(key=lambda x: (
        _SPECIAL_QUIZ_ROLE_ORDER.get(x[1].get("quiz_role", ""), 9),
        str(x[1].get("part_id", "")),
    ))

    for _, content in sq_entries:
        role_label = _SPECIAL_QUIZ_ROLE_LABEL.get(content.get("quiz_role", ""), content.get("quiz_role", ""))
        part_id = str(content.get("part_id", "-"))
        for it in content.get("items", []) or []:
            q_type = it.get("type", "")
            choices = it.get("choices", "-")
            answer = it.get("answer", "")
            category = it.get("category", "-")
            if sql_cols:
                ws.append([
                    role_label, part_id,
                    it.get("chapter_id", "-"),
                    it.get("clip_group_id", "-"),
                    it.get("is_free", "TRUE"),
                    q_type,
                    _to_sql_type(q_type),
                    _to_answer_json(q_type, answer, choices),
                    _to_answer_options_json(choices),
                    _to_match_extras_json(category) if q_type == "분류" else "{}",
                ])
            else:
                ws.append([
                    role_label, part_id,
                    it.get("chapter_id", "-"),
                    q_type,
                    it.get("difficulty", ""),
                    it.get("title", ""),
                    it.get("question", ""),
                    it.get("hint", ""),
                    choices, answer, category,
                    it.get("explanation", ""),
                ])
            ws.cell(row=ws.max_row, column=3).number_format = "@"

    last = ws.max_row
    if last > 1:
        _style_body(ws, 2, last, len(headers))
    if sql_cols:
        _set_widths(ws, [12, 8, 10, 14, 10, 12, 10, 50, 50, 40])
    else:
        _set_widths(ws, [12, 8, 10, 12, 10, 30, 40, 35, 35, 18, 22, 55])


def _build_practice_tab(wb, bp: dict, by_key: dict, sql_cols: bool = False):
    ws = wb.create_sheet("실습")
    if sql_cols:
        headers = ["챕터 구분", "clip_group_id", "is_free", "콘텐츠명",
                   "파일URL", "응답형식", "practice_role", "합격점수", "학습포인트"]
    else:
        # 제임스 본드 레퍼런스 기준 18열 형태
        headers = ["챕터 구분", "clip_group_id", "is_free", "콘텐츠명",
                   "문제", "설명", "파일URL", "실습환경", "난이도",
                   "정답", "합격점수", "응답형식",
                   "평가항목1", "평가항목1-설명", "평가항목2", "평가항목2-설명",
                   "평가항목3", "평가항목3-설명"]
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
            stage = it.get("stage", "")
            lp = it.get("learning_point", "")
            base_desc = it.get("description", "")
            merged_desc = f"■ 학습포인트: {lp}\n\n{base_desc}" if lp else base_desc
            if sql_cols:
                row_data = [
                    it.get("chapter_id", chap),
                    it.get("clip_group_id", "-"),
                    it.get("is_free", "FALSE"),
                    it.get("title", ""),
                    it.get("file_url", "-"),
                    it.get("response_type", "텍스트"),
                    _practice_role(stage),
                    it.get("passing_score", ""),
                    lp,
                ]
            else:
                row_data = [
                    it.get("chapter_id", chap),
                    it.get("clip_group_id", "-"),
                    it.get("is_free", "TRUE"),
                    it.get("title", ""),
                    it.get("question", ""),
                    merged_desc,
                    it.get("file_url", "-"),
                    it.get("environment", "ChatGPT"),
                    it.get("difficulty", ""),
                    it.get("answer", ""),
                    it.get("passing_score", ""),
                    it.get("response_type", "텍스트"),
                    _c(0, "title"), _c(0, "description"),
                    _c(1, "title"), _c(1, "description"),
                    _c(2, "title"), _c(2, "description"),
                ]
            ws.append(row_data)
            ws.cell(row=ws.max_row, column=1).number_format = "@"
    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    if sql_cols:
        _set_widths(ws, [10, 14, 10, 28, 12, 12, 14, 12, 50])
    else:
        _set_widths(ws, [10, 14, 8, 28, 40, 44, 12, 14, 10,
                         55, 12, 12, 24, 34, 24, 34, 24, 34])


def _build_story_tab(wb, bp: dict, by_key: dict):
    """챕터별 인트로 스토리 탭 — 백오피스 이미지 제작용 (씬 내러티브 + 이미지 프롬프트)."""
    ws = wb.create_sheet("스토리")
    headers = ["챕터 구분", "씬 제목", "위인 캐릭터명", "오프닝 씬", "미션 브리핑", "Scene (이미지용)"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))
    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id", "-")
        story = by_key.get(("story", chap))
        if not story:
            ws.append([chap, "-", "-", "-", "-", "-"])
            continue
        ws.append([
            chap,
            story.get("scene_title", "-"),
            story.get("character_name", "-"),
            story.get("opening_scene", "-"),
            story.get("mission_briefing", "-"),
            story.get("scene_image_prompt", "-"),
        ])
    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    _set_widths(ws, [12, 16, 14, 60, 70, 80])
    for r in ws.iter_rows(min_row=2, max_row=last, min_col=1, max_col=1):
        for cell in r:
            cell.number_format = "@"


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


def _build_course_practice_quiz_tab(wb, bp: dict, by_key: dict, run_id: str):
    """course_practice_quiz 테이블 INSERT용 탭. clip_group_id는 설정 탭에서 입력 예정."""
    ws = wb.create_sheet("course_practice_quiz")
    headers = ["course_id", "clip_id", "clip_group_id", "target", "target_id", "sequence", "is_free", "비고"]
    ws.append(headers)
    _style_header(ws, 1, len(headers))

    # 설정 탭의 course_id, practice_start_id, quiz_start_id를 읽어서 사용
    # (실제 값은 설정 탭에 입력 예정이므로 placeholder 처리)
    course_id = "[course_id 입력]"
    practice_start = 500000  # 기본값 placeholder
    quiz_start = 100000      # 기본값 placeholder

    p_seq = practice_start
    q_seq = quiz_start
    seq_num = 1

    for row in bp.get("curriculum", []) or []:
        chap = row.get("chapter_id", "")
        pset = by_key.get(("practice", chap))
        quiz_set = by_key.get(("quiz", chap))

        p_ids = []
        if pset:
            for item in pset.get("items", []) or []:
                p_ids.append(p_seq)
                p_seq += 1

        q_ids = []
        if quiz_set:
            for item in quiz_set.get("items", []) or []:
                q_ids.append(q_seq)
                q_seq += 1

        # BAD (실험) → sequence 1
        if len(p_ids) >= 1:
            ws.append([course_id, None, "[clip_group_id]", "PRACTICE", p_ids[0], 1, 1, f"{chap} BAD(실험)"])
            ws.cell(row=ws.max_row, column=1).number_format = "@"
        # GOOD (레슨) → sequence 2
        if len(p_ids) >= 2:
            ws.append([course_id, None, "[clip_group_id]", "PRACTICE", p_ids[1], 2, 1, f"{chap} GOOD(레슨)"])
            ws.cell(row=ws.max_row, column=1).number_format = "@"
        # 추가 실습(도전) → sequence 2-ext (GOOD 동일 묶음)
        if len(p_ids) >= 3:
            ws.append([course_id, None, "[clip_group_id]", "PRACTICE", p_ids[2], 2, 1, f"{chap} GOOD(도전)"])
            ws.cell(row=ws.max_row, column=1).number_format = "@"

        # 퀴즈 → sequence 3~7
        for i, qid in enumerate(q_ids[:5]):
            ws.append([course_id, None, "[clip_group_id]", "QUIZ", qid, 3 + i, 1, f"{chap} 퀴즈{i+1}"])
            ws.cell(row=ws.max_row, column=1).number_format = "@"

    last = ws.max_row
    _style_body(ws, 2, last, len(headers))
    _set_widths(ws, [20, 10, 20, 12, 14, 10, 10, 30])

    # 안내 텍스트 (별도 행)
    ws.append([])
    note_row = ws.max_row + 1
    ws.append(["※ clip_group_id는 영상 업로드 후 백오피스에서 파싱한 값을 입력하세요. course_id는 설정 탭에서 확인."])
    ws.cell(row=note_row, column=1).font = Font(name="맑은 고딕", size=10, color="71717A", italic=True)

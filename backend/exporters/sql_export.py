"""
Run 결과를 INSERT INTO SQL 파일로 내보내기.

3개 테이블: quiz / practice / course_practice_quiz
레퍼런스: aiworld/v2/reference/Table/insert_제임스본드.sql
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from ..db import get_conn


_DIFFICULTY_LEVEL = {"하": 1, "중하": 2, "중": 3, "중상": 4, "상": 5}

_QUIZ_TYPE_SQL = {
    "OX": "OX",
    "단일선택": "SINGLE",
    "복수선택": "MULTIPLE",
    "분류": "MATCH",
    "단답형": "INPUT",
}

# 개발팀이 교체할 placeholder 시작값
QUIZ_ID_START = 900001
PRACTICE_ID_START = 950001


def _esc(v: str) -> str:
    """SQL 문자열 이스케이프 (작은따옴표 → \')"""
    return v.replace("'", "\\'")


def _s(v) -> str:
    """값 → SQL 리터럴"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    return f"'{_esc(str(v))}'"


def _quiz_answer(q_type: str, answer: str) -> str:
    t = _QUIZ_TYPE_SQL.get(q_type, q_type)
    if t == "OX":
        return "1" if answer.strip().upper() == "O" else "2"
    if t == "SINGLE":
        m = re.search(r'\((\d+)\)', answer)
        return str(int(m.group(1))) if m else "1"
    if t == "MULTIPLE":
        ids = [int(x) for x in re.findall(r'\((\d+)\)', answer)]
        return json.dumps(ids, ensure_ascii=False)
    if t == "MATCH":
        parts = answer.split('/')
        groups = [[int(x) for x in re.findall(r'\d+', p)] for p in parts]
        return json.dumps(groups, ensure_ascii=False)
    if t == "INPUT":
        return json.dumps([answer.strip()], ensure_ascii=False)
    return json.dumps([answer], ensure_ascii=False)


def _quiz_answer_options(q_type: str, choices: str) -> str | None:
    t = _QUIZ_TYPE_SQL.get(q_type, q_type)
    if t == "OX":
        return json.dumps([{"id": 1, "answer": "O"}, {"id": 2, "answer": "X"}], ensure_ascii=False)
    if t == "INPUT":
        return None
    if not choices or choices.strip() == "-":
        return None
    lines = [l.strip() for l in choices.split('\n') if l.strip()]
    result = []
    for line in lines:
        m = re.match(r'^\((\d+)\)\s*(.*)', line)
        if m:
            result.append({"id": int(m.group(1)), "answer": m.group(2)})
    return json.dumps(result, ensure_ascii=False) if result else None


def _quiz_extras(q_type: str, category: str) -> str | None:
    t = _QUIZ_TYPE_SQL.get(q_type, q_type)
    if t == "MULTIPLE":
        return json.dumps({"multipleSelectCount": 2}, ensure_ascii=False)
    if t == "MATCH" and category and category.strip() != "-":
        parts = [p.strip() for p in category.split(',')]
        buckets = [{"bucketName": p, "bucketSequence": i + 1} for i, p in enumerate(parts)]
        return json.dumps({"matchBuckets": buckets}, ensure_ascii=False)
    return None


def _practice_ai_prompt(it: dict) -> str | None:
    crs = it.get("criteria") or []
    if not crs:
        return None
    result = {"criteria": [
        {"criterion": c.get("title", ""), "description": c.get("description", ""), "evaluationCriterion": []}
        for c in crs
    ]}
    return json.dumps(result, ensure_ascii=False)


def build_sql(run_id: str) -> tuple[str, str]:
    """INSERT SQL 문자열 생성. (filename, sql_text)"""
    with get_conn() as conn:
        run = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ValueError(f"run not found: {run_id}")
        bp = conn.execute(
            "SELECT content_json FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        comps = conn.execute(
            """
            SELECT c.type, c.chapter_id, c.content_json
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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    course_name = blueprint.get("course_name", run_id)
    curriculum = blueprint.get("curriculum") or []

    lines: list[str] = [
        f"-- AI World Harness SQL Export",
        f"-- 코스: {course_name}",
        f"-- Run ID: {run_id}",
        f"-- 생성일시: {now}",
        f"-- ⚠️  ID는 placeholder. 개발팀이 실제 DB 값으로 교체 후 실행.",
        f"-- quiz ID 시작값:     {QUIZ_ID_START}",
        f"-- practice ID 시작값: {PRACTICE_ID_START}",
        f"-- course_id / clip_group_id: 개발팀 세팅",
        "",
        "use fastcampus_prod;",
        "",
    ]

    # --- practice ---
    practice_vals: list[str] = []
    practice_id = PRACTICE_ID_START

    for chap_row in curriculum:
        chap = chap_row.get("chapter_id", "")
        pset = by_key.get(("practice", chap))
        if not pset:
            continue
        for it in pset.get("items", []) or []:
            lp = it.get("learning_point", "")
            base_desc = it.get("description", "")
            merged_desc = f"■ 학습포인트: {lp}\n\n{base_desc}" if lp else base_desc
            difficulty = it.get("difficulty", "중")
            level = _DIFFICULTY_LEVEL.get(difficulty, 3)
            ai_prompt = _practice_ai_prompt(it)
            passing_score = it.get("passing_score") or "75"

            vals = ", ".join([
                _s(str(practice_id)),
                _s("FASTCAMPUS"),
                _s(it.get("environment", "ChatGPT")),
                "NULL",                           # sub_type
                _s("TEXT"),                       # output_type
                _s(str(level)),
                _s(it.get("title", "")),
                _s(merged_desc),
                _s(it.get("question", "")),
                _s(it.get("answer", "")),
                _s(ai_prompt),                    # ai_prompt (criteria JSON)
                _s(str(passing_score)),
                "NULL",                           # extras
                _s(now),
                _s(now),
            ])
            practice_vals.append(f"\t({vals})")
            practice_id += 1

    if practice_vals:
        lines.append("INSERT INTO `practice` (`id`, `site`, `type`, `sub_type`, `output_type`, `level`, `title`, `description`, `question`, `answer`, `ai_prompt`, `pass_score`, `extras`, `created_at`, `updated_at`)")
        lines.append("VALUES")
        lines.append(",\n".join(practice_vals) + ";")
        lines.append("")

    # --- quiz ---
    quiz_vals: list[str] = []
    quiz_id = QUIZ_ID_START

    for chap_row in curriculum:
        chap = chap_row.get("chapter_id", "")
        qset = by_key.get(("quiz", chap))
        if not qset:
            continue
        for it in qset.get("items", []) or []:
            q_type = it.get("type", "")
            choices = it.get("choices", "-")
            answer = it.get("answer", "")
            category = it.get("category", "-")
            difficulty = it.get("difficulty", "중")
            level = _DIFFICULTY_LEVEL.get(difficulty, 3)

            answer_val = _quiz_answer(q_type, answer)
            answer_options = _quiz_answer_options(q_type, choices)
            extras = _quiz_extras(q_type, category)

            vals = ", ".join([
                _s(str(quiz_id)),
                _s("FASTCAMPUS"),
                _s("NORMAL"),
                _s(_QUIZ_TYPE_SQL.get(q_type, q_type)),
                _s(it.get("title", "")),
                _s(it.get("question", "")),
                _s(it.get("explanation", "")),
                _s(it.get("hint", "")),
                "NULL",                           # score
                _s(str(level)),
                _s(answer_val),
                _s(answer_options) if answer_options is not None else "NULL",
                _s(extras) if extras is not None else "NULL",
                _s(now),
                _s(now),
            ])
            quiz_vals.append(f"\t({vals})")
            quiz_id += 1

    if quiz_vals:
        lines.append("INSERT INTO `quiz` (`id`, `site`, `state`, `type`, `title`, `question`, `explanation`, `hint`, `score`, `level`, `answer`, `answer_options`, `extras`, `created_at`, `updated_at`)")
        lines.append("VALUES")
        lines.append(",\n".join(quiz_vals) + ";")
        lines.append("")

    # --- course_practice_quiz ---
    cpq_vals: list[str] = []
    p_cursor = PRACTICE_ID_START
    q_cursor = QUIZ_ID_START

    for chap_row in curriculum:
        chap = chap_row.get("chapter_id", "")
        pset = by_key.get(("practice", chap))
        qset = by_key.get(("quiz", chap))
        p_items = (pset.get("items", []) or []) if pset else []
        q_items = (qset.get("items", []) or []) if qset else []

        seq = 1
        for i, _ in enumerate(p_items):
            vals = ", ".join([
                "COURSE_ID",
                "NULL",
                f"CLIP_GROUP_ID",
                _s("PRACTICE"),
                str(p_cursor + i),
                str(seq),
                "1",
                "CURRENT_TIMESTAMP",
                "CURRENT_TIMESTAMP",
            ])
            cpq_vals.append(f"\t({vals})")
            seq += 1

        for i, _ in enumerate(q_items[:5]):
            vals = ", ".join([
                "COURSE_ID",
                "NULL",
                f"CLIP_GROUP_ID",
                _s("QUIZ"),
                str(q_cursor + i),
                str(seq),
                "1",
                "CURRENT_TIMESTAMP",
                "CURRENT_TIMESTAMP",
            ])
            cpq_vals.append(f"\t({vals})")
            seq += 1

        p_cursor += len(p_items)
        q_cursor += len(q_items)

    if cpq_vals:
        lines.append("INSERT INTO `course_practice_quiz` (`course_id`, `clip_id`, `clip_group_id`, `target`, `target_id`, `sequence`, `is_free`, `created_at`, `updated_at`)")
        lines.append("VALUES")
        lines.append(",\n".join(cpq_vals) + ";")
        lines.append("")

    sql_text = "\n".join(lines)
    safe_name = course_name.replace("/", "_").replace("\\", "_")[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"[AW] {safe_name}_{ts}.sql"
    return filename, sql_text

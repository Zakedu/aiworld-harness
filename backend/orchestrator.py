"""
Orchestrator — 전체 파이프라인 제어.

흐름:
1. Director가 기획서 생성 → 사용자 승인 대기 (승인 없이 다음 단계 금지)
2. 승인 후, 챕터 × 컴포넌트 매트릭스로 병렬 생성 (quiz + practice) 시작
3. 생성 → schema 검증 → rubric 검증 (반대 모델) → 통과/재생성/플래그
4. 항목 단위 재생성은 별도 API (regenerate_component_item)로 처리
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any
from .config import CROSS_MATRIX, MAX_REGEN_RETRIES
from .db import get_conn
from .ws import ws_manager
from .agents import course_planner, quiz_generator, practice_generator, material_writer, figure_rationale, story_writer, special_quiz_generator
from .validators.schema_validator import validate_component
from .validators.rubric_validator import rubric_validate, extract_flags_from_results
from .validators.glossary_validator import validate_component as glossary_validate


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def emit(run_id: str, event: str, payload: dict):
    await ws_manager.push(run_id, event, payload)


# ------------------------------------------------------------------
# Director
# ------------------------------------------------------------------

async def run_planning(run_id: str, inputs: dict, mixer: dict) -> dict:
    provider, _validator = CROSS_MATRIX["course_overview"]
    await emit(run_id, "blueprint.started", {"provider": provider})

    try:
        blueprint = await course_planner.generate_blueprint(inputs, mixer, provider=provider)
    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e)[:500]}"
        await emit(run_id, "blueprint.error", {"error": err_msg, "provider": provider})
        with get_conn() as conn:
            conn.execute("UPDATE runs SET status='error' WHERE run_id=?", (run_id,))
            conn.commit()
        return {"error": err_msg}

    blueprint_id = new_id("bp")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO blueprints(blueprint_id, run_id, version, content_json, generator_model) VALUES (?,?,?,?,?)",
            (blueprint_id, run_id, 1, json.dumps(blueprint, ensure_ascii=False), provider),
        )
        conn.execute("UPDATE runs SET status='awaiting_approval' WHERE run_id=?", (run_id,))
        conn.commit()

    await emit(run_id, "blueprint.completed", {"blueprint_id": blueprint_id, "content": blueprint})
    return {"blueprint_id": blueprint_id, "content": blueprint}


async def approve_blueprint(run_id: str, blueprint_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE blueprints SET approved_at=CURRENT_TIMESTAMP WHERE blueprint_id=?", (blueprint_id,))
        conn.execute("UPDATE runs SET status='generating' WHERE run_id=?", (run_id,))
        conn.commit()
    # 승인 후 실제 콘텐츠 생성 시작 (비동기)
    asyncio.create_task(_generate_all_components(run_id, blueprint_id))


# ------------------------------------------------------------------
# 컴포넌트 병렬 생성
# ------------------------------------------------------------------

async def _generate_all_components(run_id: str, blueprint_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content_json FROM blueprints WHERE blueprint_id=?", (blueprint_id,)
        ).fetchone()
    blueprint = json.loads(row["content_json"])
    curriculum = blueprint.get("curriculum", [])

    # Step A: 위인 선정 배경 (코스당 1개)
    # run의 inputs_json에서 주제/학습대상 조회
    with get_conn() as conn:
        r = conn.execute("SELECT inputs_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
    inputs = json.loads(r["inputs_json"]) if r else {}
    await _generate_figure_rationale(run_id, blueprint_id, blueprint, inputs)

    # Step B: 학습자료 + 스토리 병렬 생성 (퀴즈·실습의 근거 자료)
    material_tasks = [
        _generate_material(run_id, blueprint_id, blueprint, ch) for ch in curriculum
    ]
    story_tasks = [
        _generate_story_chapter(run_id, blueprint_id, blueprint, ch) for ch in curriculum
    ]
    await asyncio.gather(*material_tasks, *story_tasks, return_exceptions=True)

    # Step C: 학습자료 기반으로 퀴즈·실습 병렬 생성
    tasks = []
    for chapter in curriculum:
        tasks.append(_generate_and_validate(run_id, blueprint_id, blueprint, chapter, "quiz"))
        tasks.append(_generate_and_validate(run_id, blueprint_id, blueprint, chapter, "practice"))
    await asyncio.gather(*tasks, return_exceptions=True)

    # Step D: 파트 티저 / 파트 종합 / 최종 회고 생성
    await _generate_special_quizzes(run_id, blueprint_id, blueprint, curriculum)

    # 누락 컴포넌트 감지 (병렬 생성 중 조용히 실패한 항목)
    missing: list[dict] = []
    with get_conn() as conn:
        for ch in curriculum:
            cid = ch["chapter_id"]
            for ctype in ("material", "story", "quiz", "practice"):
                row = conn.execute(
                    "SELECT 1 FROM components WHERE run_id=? AND type=? AND chapter_id=? LIMIT 1",
                    (run_id, ctype, cid),
                ).fetchone()
                if not row:
                    missing.append({
                        "chapter_id": cid,
                        "chapter_name": ch.get("chapter_name", ""),
                        "type": ctype,
                    })
    if missing:
        await emit(run_id, "run.missing_components", {"missing": missing})

    with get_conn() as conn:
        conn.execute("UPDATE runs SET status='reviewing' WHERE run_id=?", (run_id,))
        conn.commit()
    await emit(run_id, "run.completed", {})


async def _generate_and_validate(
    run_id: str,
    blueprint_id: str,
    blueprint: dict,
    chapter: dict,
    component_type: str,
):
    gen_provider, val_provider = CROSS_MATRIX[component_type]
    chapter_id = chapter["chapter_id"]
    component_id = new_id(f"{component_type}-{chapter_id}")
    await emit(run_id, "component.generating", {
        "component_id": component_id, "type": component_type,
        "chapter_id": chapter_id, "generator": gen_provider,
    })

    # 학습자료 조회 (Step B에서 생성한 내용)
    with get_conn() as conn:
        mat = conn.execute(
            "SELECT content_json FROM components WHERE run_id=? AND type='material' AND chapter_id=? ORDER BY version DESC LIMIT 1",
            (run_id, chapter_id),
        ).fetchone()
    if mat:
        mat_obj = json.loads(mat["content_json"])
        material_excerpt = "\n\n".join(
            f"## {s.get('heading','')}\n{s.get('body','')}"
            for s in _body_sections(mat_obj.get("sections") or [])
        )[:6000]  # 브릿지 섹션 제외 — 교육 본문만 전달
    else:
        # fallback: material 생성 실패 시 최소 요약
        material_excerpt = (
            f"[{chapter['chapter_name']}] 프롬프트 기법: {chapter['prompt_technique']}\n"
            f"파트: {chapter['part_name']}"
        )

    # run의 mixer 로드 (퀴즈·실습 수량/난이도 분포/타깃 AI 등 신규 필드 사용)
    with get_conn() as conn:
        r = conn.execute("SELECT mixer_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
    mixer = json.loads(r["mixer_json"]) if r and r["mixer_json"] else {}

    try:
        if component_type == "quiz":
            content = await quiz_generator.generate_quiz_chapter(chapter, blueprint, material_excerpt, mixer, gen_provider)
        else:
            content = await practice_generator.generate_practice_chapter(chapter, blueprint, material_excerpt, mixer, gen_provider)
    except Exception as e:
        await emit(run_id, "component.error", {"component_id": component_id, "error": str(e)})
        return

    version = 1
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (component_id, run_id, blueprint_id, component_type, chapter_id, version,
             gen_provider, val_provider, json.dumps(content, ensure_ascii=False), "generated"),
        )
        conn.commit()
    await emit(run_id, "component.generated", {"component_id": component_id, "type": component_type, "chapter_id": chapter_id})

    # ------- 검증 루프 -------
    current_content = content
    current_component_id = component_id
    current_version = version
    retries = 0
    while True:
        # 1) Schema validator (코드)
        schema_result = validate_component(component_type, current_content)
        # 2) Rubric validator (LLM, 반대 모델) — 실패 시 조용히 무시되지 않도록 try/except
        try:
            rubric_result = await rubric_validate(component_type, current_content, val_provider)
        except Exception as val_err:
            import logging
            logging.warning(f"[Validator] rubric_validate failed ({component_type} {chapter_id}): {val_err}")
            with get_conn() as conn:
                conn.execute("UPDATE components SET status='validation_error' WHERE component_id=?",
                             (current_component_id,))
                conn.commit()
            await emit(run_id, "component.validation_error", {
                "component_id": current_component_id, "type": component_type,
                "chapter_id": chapter_id, "error": str(val_err)[:300]
            })
            return
        passed = schema_result["passed"] and rubric_result.get("passed", False)

        with get_conn() as conn:
            conn.execute(
                "INSERT INTO validations(validation_id, component_id, validator_type, validator_model, rubric_results_json, overall_score, passed) VALUES (?,?,?,?,?,?,?)",
                (new_id("val"), current_component_id, "schema+rubric", val_provider,
                 json.dumps({"schema": schema_result, "rubric": rubric_result}, ensure_ascii=False),
                 rubric_result.get("overall_score", 0), 1 if passed else 0),
            )
            conn.execute("UPDATE components SET status=? WHERE component_id=?",
                         ("passed" if passed else "flagged", current_component_id))
            # Schema validator 에러는 SCHEMA 플래그로 삽입
            for err in schema_result["errors"]:
                conn.execute(
                    "INSERT INTO flags(flag_id, component_id, run_id, flag_type, severity, location_path, reason, guide, origin_text) VALUES (?,?,?,?,?,?,?,?,?)",
                    (new_id("flag"), current_component_id, run_id, "SCHEMA", "상",
                     err["path"], err["reason"], "스키마 v1 규칙 확인 — 수동 편집 또는 재생성", ""),
                )
            # Rubric validator 결과 → 플래그
            for f in extract_flags_from_results(current_component_id, run_id, component_type, rubric_result):
                conn.execute(
                    "INSERT INTO flags(flag_id, component_id, run_id, flag_type, severity, location_path, reason, guide, origin_text) VALUES (?,?,?,?,?,?,?,?,?)",
                    (new_id("flag"), f["component_id"], f["run_id"], f["flag_type"], f["severity"],
                     f["location_path"], f["reason"], f["guide"], f["origin_text"]),
                )
            conn.commit()

        if passed or retries >= MAX_REGEN_RETRIES:
            await emit(run_id, "component.validated" if passed else "component.flagged", {
                "component_id": current_component_id, "type": component_type, "chapter_id": chapter_id,
                "passed": passed, "score": rubric_result.get("overall_score", 0),
            })
            return

        # 재생성: schema 에러 중심 요약 + rubric FAIL 항목을 지시문으로
        retries += 1
        reason = "자동 재생성: " + "; ".join(e["reason"] for e in schema_result["errors"][:3])
        await emit(run_id, "component.regenerating", {
            "component_id": current_component_id, "type": component_type, "chapter_id": chapter_id,
            "retry": retries, "reason": reason,
        })

        # 새 버전 생성
        if component_type == "quiz":
            current_content = await quiz_generator.generate_quiz_chapter(chapter, blueprint, material_excerpt, {}, gen_provider)
        else:
            current_content = await practice_generator.generate_practice_chapter(chapter, blueprint, material_excerpt, {}, gen_provider)
        new_component_id = new_id(f"{component_type}-{chapter_id}")
        current_version += 1
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status, parent_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (new_component_id, run_id, blueprint_id, component_type, chapter_id, current_version,
                 gen_provider, val_provider, json.dumps(current_content, ensure_ascii=False), "generated", current_version - 1),
            )
            conn.execute(
                "INSERT INTO regenerations(regen_id, source_component_id, target_component_id, scope, user_instruction, generator_model, validator_model) VALUES (?,?,?,?,?,?,?)",
                (new_id("regen"), current_component_id, new_component_id, "component",
                 f"auto retry #{retries}: {reason}", gen_provider, val_provider),
            )
            conn.commit()
        current_component_id = new_component_id
        # 새 버전 카드를 UI에 알리기 (type/chapter_id 포함)
        await emit(run_id, "component.generating", {
            "component_id": current_component_id, "type": component_type,
            "chapter_id": chapter_id, "generator": gen_provider,
        })


# ------------------------------------------------------------------
# 파트 인트로 / 학습자료 생성 + 검증
# ------------------------------------------------------------------

async def _generate_figure_rationale(run_id: str, blueprint_id: str, blueprint: dict, inputs: dict):
    """코스당 1개 — 위인 선정 배경."""
    gen, val = CROSS_MATRIX["figure_rationale"]
    cid = new_id("figure_rationale")
    await emit(run_id, "component.generating", {
        "component_id": cid, "type": "figure_rationale",
        "chapter_id": "-", "generator": gen,
    })
    try:
        content = await figure_rationale.generate_rationale(inputs, blueprint, {}, provider=gen)
    except Exception as e:
        await emit(run_id, "component.error", {"component_id": cid, "error": str(e)})
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, run_id, blueprint_id, "figure_rationale", "-",
             1, gen, val, json.dumps(content, ensure_ascii=False), "generated"),
        )
        conn.commit()
    await emit(run_id, "component.generated", {"component_id": cid, "type": "figure_rationale", "chapter_id": "-"})
    await _run_validators(run_id, cid, "figure_rationale", content, val)


async def _generate_material(run_id: str, blueprint_id: str, blueprint: dict, chapter: dict):
    gen, val = CROSS_MATRIX["material"]
    chapter_id = chapter["chapter_id"]
    cid = new_id(f"material-{chapter_id}")
    await emit(run_id, "component.generating", {
        "component_id": cid, "type": "material",
        "chapter_id": chapter_id, "generator": gen,
    })
    with get_conn() as conn:
        r = conn.execute("SELECT mixer_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
    mixer = json.loads(r["mixer_json"]) if r and r["mixer_json"] else {}
    try:
        content = await material_writer.generate_material(chapter, blueprint, mixer, provider=gen)
    except Exception as e:
        await emit(run_id, "component.error", {"component_id": cid, "error": str(e)})
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, run_id, blueprint_id, "material", chapter_id, 1, gen, val,
             json.dumps(content, ensure_ascii=False), "generated"),
        )
        conn.commit()
    await emit(run_id, "component.generated", {"component_id": cid, "type": "material", "chapter_id": chapter_id})
    await _run_validators(run_id, cid, "material", content, val, chapter_id=chapter_id)


async def _generate_story_chapter(run_id: str, blueprint_id: str, blueprint: dict, chapter: dict):
    gen, val = CROSS_MATRIX["story"]
    chapter_id = chapter["chapter_id"]
    cid = new_id(f"story-{chapter_id}")
    await emit(run_id, "component.generating", {
        "component_id": cid, "type": "story",
        "chapter_id": chapter_id, "generator": gen,
    })
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content_json FROM components WHERE run_id=? AND type='figure_rationale' ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    figure_content = json.loads(row["content_json"]) if row else None
    try:
        content = await story_writer.generate_story(chapter, blueprint, figure_content, provider=gen)
    except Exception as e:
        await emit(run_id, "component.error", {"component_id": cid, "error": str(e)})
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, run_id, blueprint_id, "story", chapter_id, 1, gen, val,
             json.dumps(content, ensure_ascii=False), "generated"),
        )
        conn.commit()
    await emit(run_id, "component.generated", {"component_id": cid, "type": "story", "chapter_id": chapter_id})


async def _generate_special_quizzes(
    run_id: str, blueprint_id: str, blueprint: dict, curriculum: list[dict]
):
    """Step D: 파트 티저 + 파트 종합 + 최종 회고 생성."""
    gen, val = CROSS_MATRIX["special_quiz"]

    # 챕터를 파트별로 그룹화
    parts: dict[str, dict] = {}
    for ch in curriculum:
        cid = ch["chapter_id"]
        part_num = cid.split("-")[0]
        if part_num not in parts:
            parts[part_num] = {"part_id": part_num, "part_name": ch.get("part_name", f"파트 {part_num}"), "chapters": []}
        parts[part_num]["chapters"].append(ch)

    # DB에서 각 챕터 학습자료 발췌 수집
    def _collect_excerpts(run_id: str, chapter_ids: list[str]) -> dict[str, str]:
        excerpts: dict[str, str] = {}
        with get_conn() as conn:
            for cid in chapter_ids:
                row = conn.execute(
                    "SELECT content_json FROM components WHERE run_id=? AND type='material' AND chapter_id=? ORDER BY version DESC LIMIT 1",
                    (run_id, cid),
                ).fetchone()
                if row:
                    mat = json.loads(row["content_json"])
                    sections = mat.get("sections", [])
                    excerpts[cid] = " ".join(s.get("body", "")[:300] for s in sections)[:800]
        return excerpts

    async def _save_special(role: str, part_id: str, content: dict):
        chapter_id = f"{part_id}-{role}"
        cid = new_id(f"special_quiz-{chapter_id}")
        content["quiz_role"] = role
        content["part_id"] = part_id
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (cid, run_id, blueprint_id, "special_quiz", chapter_id, 1, gen, val,
                 json.dumps(content, ensure_ascii=False), "generated"),
            )
            conn.commit()
        await emit(run_id, "component.generated", {
            "component_id": cid, "type": "special_quiz",
            "chapter_id": chapter_id, "quiz_role": role,
        })
        await _run_validators(run_id, cid, "special_quiz", content, val, chapter_id=chapter_id)

    # 각 파트 티저 + 종합 병렬 생성
    part_tasks = []
    for part_num, part_info in parts.items():
        chapters = part_info["chapters"]
        excerpts = _collect_excerpts(run_id, [ch["chapter_id"] for ch in chapters])

        async def _gen_part(pnum=part_num, pname=part_info["part_name"], chs=chapters, exs=excerpts):
            try:
                teaser = await special_quiz_generator.generate_part_teaser(pnum, pname, chs, blueprint, gen)
                await _save_special("teaser", pnum, teaser)
            except Exception as e:
                await emit(run_id, "component.error", {"type": "special_quiz", "quiz_role": "teaser", "error": str(e)})
            try:
                summary = await special_quiz_generator.generate_part_summary(pnum, pname, chs, blueprint, exs, gen)
                await _save_special("part_summary", pnum, summary)
            except Exception as e:
                await emit(run_id, "component.error", {"type": "special_quiz", "quiz_role": "part_summary", "error": str(e)})

        part_tasks.append(_gen_part())

    await asyncio.gather(*part_tasks, return_exceptions=True)

    # 최종 회고
    all_parts_info = [
        {"part_id": pnum, "part_name": pinfo["part_name"], "chapters": pinfo["chapters"]}
        for pnum, pinfo in parts.items()
    ]
    try:
        final = await special_quiz_generator.generate_final_review(blueprint, all_parts_info, gen)
        await _save_special("final_review", "final", final)
    except Exception as e:
        await emit(run_id, "component.error", {"type": "special_quiz", "quiz_role": "final_review", "error": str(e)})



async def _run_validators(run_id: str, component_id: str, component_type: str, content: dict, val_provider: str, chapter_id: str = "-"):
    """단발성 검증 (재생성 루프 없음) — part_intro·material용."""
    schema_result = validate_component(component_type, content) if component_type in {"material"} else {"passed": True, "errors": []}
    rubric_result = await rubric_validate(component_type, content, val_provider)
    glossary_violations = glossary_validate(content, component_type)
    passed = schema_result.get("passed", True) and rubric_result.get("passed", False)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO validations(validation_id, component_id, validator_type, validator_model, rubric_results_json, overall_score, passed) VALUES (?,?,?,?,?,?,?)",
            (new_id("val"), component_id, "schema+rubric", val_provider,
             json.dumps({"schema": schema_result, "rubric": rubric_result}, ensure_ascii=False),
             rubric_result.get("overall_score", 0), 1 if passed else 0),
        )
        conn.execute("UPDATE components SET status=? WHERE component_id=?",
                     ("passed" if passed else "flagged", component_id))
        for err in schema_result.get("errors", []):
            conn.execute(
                "INSERT INTO flags(flag_id, component_id, run_id, flag_type, severity, location_path, reason, guide, origin_text) VALUES (?,?,?,?,?,?,?,?,?)",
                (new_id("flag"), component_id, run_id, "SCHEMA", "상",
                 err["path"], err["reason"], "스키마 v1 규칙 확인", ""),
            )
        for f in extract_flags_from_results(component_id, run_id, component_type, rubric_result):
            conn.execute(
                "INSERT INTO flags(flag_id, component_id, run_id, flag_type, severity, location_path, reason, guide, origin_text) VALUES (?,?,?,?,?,?,?,?,?)",
                (new_id("flag"), f["component_id"], f["run_id"], f["flag_type"], f["severity"],
                 f["location_path"], f["reason"], f["guide"], f["origin_text"]),
            )
        sev_map = {"error": "상", "warn": "중", "info": "하"}
        for v in glossary_violations:
            conn.execute(
                "INSERT INTO flags(flag_id, component_id, run_id, flag_type, severity, location_path, reason, guide, origin_text) VALUES (?,?,?,?,?,?,?,?,?)",
                (new_id("flag"), component_id, run_id, "GLOSSARY",
                 sev_map.get(v.get("severity", "warn"), "중"),
                 "glossary", v["message"], "glossary.yaml 참조", ""),
            )
        conn.commit()
    await emit(run_id, "component.validated" if passed else "component.flagged",
               {"component_id": component_id, "type": component_type, "chapter_id": chapter_id,
                "passed": passed, "score": rubric_result.get("overall_score", 0)})


# ------------------------------------------------------------------
# 항목 단위 재생성 (Screen 3의 카드 [재생성] 버튼)
# ------------------------------------------------------------------

async def regenerate_chapter(run_id: str, chapter_id: str, instruction: str, components: list):
    """
    특정 챕터의 학습자료·퀴즈·실습을 사용자 피드백과 함께 다시 생성.

    순서:
      1. material 재생성 (피드백 반영) → 검증 → 새 버전 저장
      2. (업데이트된 material 본문 기반) quiz 재생성 → 교차검증
      3. practice 재생성 → 교차검증
    """
    with get_conn() as conn:
        bp_row = conn.execute(
            "SELECT blueprint_id, content_json FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    if not bp_row:
        await emit(run_id, "chapter.regen_error", {"error": "blueprint not found", "chapter_id": chapter_id})
        return
    blueprint = json.loads(bp_row["content_json"])
    blueprint_id = bp_row["blueprint_id"]
    chapter = next((c for c in blueprint.get("curriculum", []) if c["chapter_id"] == chapter_id), None)
    if not chapter:
        await emit(run_id, "chapter.regen_error", {"error": f"chapter {chapter_id} not found"})
        return

    await emit(run_id, "chapter.regen_started", {
        "chapter_id": chapter_id, "components": components, "instruction": instruction
    })

    with get_conn() as conn:
        conn.execute("UPDATE runs SET status='generating' WHERE run_id=?", (run_id,))
        conn.commit()

    # material 재생성 시 quiz·practice 자동 cascade
    if "material" in components:
        components = list(set(components) | {"quiz", "practice"})

    updated_material = None

    # 1) material
    if "material" in components:
        gen, val = CROSS_MATRIX["material"]
        cid = new_id(f"material-{chapter_id}")
        await emit(run_id, "component.generating", {
            "component_id": cid, "type": "material", "chapter_id": chapter_id, "generator": gen,
        })
        try:
            content = await material_writer.generate_material(
                chapter, blueprint,
                {"figure_voice": "중간", "_user_feedback": instruction},
                provider=gen,
            )
        except Exception as e:
            await emit(run_id, "component.error", {"component_id": cid, "error": str(e)})
            content = None
        if content:
            prev_ver = _latest_version(run_id, "material", chapter_id)
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status, parent_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (cid, run_id, blueprint_id, "material", chapter_id, prev_ver + 1,
                     gen, val, json.dumps(content, ensure_ascii=False), "generated", prev_ver),
                )
                conn.execute(
                    "INSERT INTO regenerations(regen_id, source_component_id, target_component_id, scope, user_instruction, generator_model, validator_model) VALUES (?,?,?,?,?,?,?)",
                    (new_id("regen"), None, cid, "chapter", instruction, gen, val),
                )
                conn.commit()
            await emit(run_id, "component.generated", {"component_id": cid, "type": "material", "chapter_id": chapter_id})
            await _run_validators(run_id, cid, "material", content, val, chapter_id=chapter_id)
            updated_material = content

    mat_excerpt = _material_excerpt(run_id, chapter, updated_material)

    if "quiz" in components:
        await _regen_single(run_id, blueprint_id, blueprint, chapter, "quiz", mat_excerpt, instruction)
    if "practice" in components:
        await _regen_single(run_id, blueprint_id, blueprint, chapter, "practice", mat_excerpt, instruction)

    with get_conn() as conn:
        conn.execute("UPDATE runs SET status='reviewing' WHERE run_id=?", (run_id,))
        conn.commit()
    await emit(run_id, "chapter.regen_completed", {"chapter_id": chapter_id})


def _latest_version(run_id, comp_type, chapter_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(version) AS v FROM components WHERE run_id=? AND type=? AND chapter_id=?",
            (run_id, comp_type, chapter_id),
        ).fetchone()
    return (row["v"] or 0) if row else 0


_BRIDGE_KINDS = {"bridge_opener", "bridge_demo", "bridge_preview"}


def _body_sections(sections: list) -> list:
    return [s for s in sections if s.get("kind") not in _BRIDGE_KINDS]


def _material_excerpt(run_id, chapter, material_content):
    if material_content:
        return "\n\n".join(
            f"## {s.get('heading','')}\n{s.get('body','')}"
            for s in _body_sections(material_content.get("sections") or [])
        )[:6000]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content_json FROM components WHERE run_id=? AND type='material' AND chapter_id=? ORDER BY version DESC LIMIT 1",
            (run_id, chapter["chapter_id"]),
        ).fetchone()
    if row:
        m = json.loads(row["content_json"])
        return "\n\n".join(
            f"## {s.get('heading','')}\n{s.get('body','')}"
            for s in _body_sections(m.get("sections") or [])
        )[:6000]
    return f"[{chapter.get('chapter_name','')}] 기법: {chapter.get('prompt_technique','')}"


async def _regen_single(run_id, blueprint_id, blueprint, chapter, component_type, mat_excerpt, instruction):
    gen_provider, val_provider = CROSS_MATRIX[component_type]
    chapter_id = chapter["chapter_id"]
    cid = new_id(f"{component_type}-{chapter_id}")
    await emit(run_id, "component.generating", {
        "component_id": cid, "type": component_type, "chapter_id": chapter_id, "generator": gen_provider,
    })
    try:
        mixer_with_feedback = {"_user_feedback": instruction}
        if component_type == "quiz":
            content = await quiz_generator.generate_quiz_chapter(chapter, blueprint, mat_excerpt, mixer_with_feedback, gen_provider)
        else:
            content = await practice_generator.generate_practice_chapter(chapter, blueprint, mat_excerpt, mixer_with_feedback, gen_provider)
    except Exception as e:
        await emit(run_id, "component.error", {"component_id": cid, "error": str(e)})
        return

    prev_ver = _latest_version(run_id, component_type, chapter_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status, parent_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, run_id, blueprint_id, component_type, chapter_id, prev_ver + 1,
             gen_provider, val_provider, json.dumps(content, ensure_ascii=False), "generated", prev_ver),
        )
        conn.execute(
            "INSERT INTO regenerations(regen_id, source_component_id, target_component_id, scope, user_instruction, generator_model, validator_model) VALUES (?,?,?,?,?,?,?)",
            (new_id("regen"), None, cid, "chapter", instruction, gen_provider, val_provider),
        )
        conn.commit()
    await emit(run_id, "component.generated", {"component_id": cid, "type": component_type, "chapter_id": chapter_id})
    await _run_validators(run_id, cid, component_type, content, val_provider, chapter_id=chapter_id)


async def regenerate_item(
    component_id: str,
    item_index: int,
    user_instruction: str,
    flag_id=None,   # Optional[str] — Python 3.9 호환 위해 단순 annotation
) -> dict:
    """컴포넌트 내 특정 item 1개만 재생성하고, 새 버전을 저장."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json FROM components WHERE component_id=?",
            (component_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"component not found: {component_id}")
        blueprint_row = conn.execute(
            "SELECT content_json FROM blueprints WHERE blueprint_id=?", (row["blueprint_id"],)
        ).fetchone()
        flag_row = None
        if flag_id:
            flag_row = conn.execute(
                "SELECT reason, guide, location_path FROM flags WHERE flag_id=?", (flag_id,)
            ).fetchone()
    blueprint = json.loads(blueprint_row["content_json"])
    chapter = next((c for c in blueprint["curriculum"] if c["chapter_id"] == row["chapter_id"]), {})
    old_content = json.loads(row["content_json"])
    items = old_content.get("items", [])
    if item_index >= len(items):
        raise IndexError("item_index out of range")
    original_item = items[item_index]
    siblings = [it for i, it in enumerate(items) if i != item_index]
    flag_reason = (flag_row["reason"] if flag_row else "(no flag reference)")

    # 재생성 (동일 모델 — 교차검증 매트릭스 유지)
    if row["type"] == "practice":
        new_item = await practice_generator.regenerate_practice_item(
            original_item, blueprint, chapter, siblings, user_instruction, flag_reason,
            provider=row["generator_model"],
        )
    elif row["type"] == "quiz":
        new_item = await quiz_generator.regenerate_quiz_item(
            original_item, blueprint, chapter, siblings, user_instruction, flag_reason,
            provider=row["generator_model"],
        )
    else:
        raise NotImplementedError(f"item-level regenerate not supported for type={row['type']}")

    items[item_index] = new_item  # type: ignore
    new_content = {**old_content, "items": items}
    new_version = row["version"] + 1
    new_cid = new_id(f"{row['type']}-{row['chapter_id']}")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO components(component_id, run_id, blueprint_id, type, chapter_id, version, generator_model, validator_model, content_json, status, parent_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (new_cid, row["run_id"], row["blueprint_id"], row["type"], row["chapter_id"], new_version,
             row["generator_model"], row["validator_model"], json.dumps(new_content, ensure_ascii=False),
             "generated", row["version"]),
        )
        conn.execute(
            "INSERT INTO regenerations(regen_id, source_component_id, target_component_id, flag_id, scope, user_instruction, generator_model, validator_model) VALUES (?,?,?,?,?,?,?,?)",
            (new_id("regen"), component_id, new_cid, flag_id, "item", user_instruction,
             row["generator_model"], row["validator_model"]),
        )
        if flag_id:
            conn.execute("UPDATE flags SET resolved=1, resolution='regenerated', resolved_at=CURRENT_TIMESTAMP WHERE flag_id=?", (flag_id,))
        conn.commit()

    await emit(row["run_id"], "component.regenerated", {
        "source": component_id, "target": new_cid, "item_index": item_index,
    })
    return {"new_component_id": new_cid, "new_content": new_content}


# ------------------------------------------------------------------
# 재검증 — 기존 generated/validation_error 컴포넌트 일괄 검증
# ------------------------------------------------------------------

async def revalidate_run(run_id: str):
    """generated 또는 validation_error 상태 컴포넌트 전체 재검증."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.component_id, c.type, c.chapter_id, c.content_json, c.validator_model
            FROM components c
            INNER JOIN (
                SELECT type, chapter_id, MAX(version) AS maxv
                FROM components WHERE run_id=?
                GROUP BY type, chapter_id
            ) m ON c.type=m.type AND c.chapter_id=m.chapter_id AND c.version=m.maxv
            WHERE c.run_id=? AND c.status IN ('generated','validation_error')
            """,
            (run_id, run_id),
        ).fetchall()

    if not rows:
        return {"revalidated": 0}

    await emit(run_id, "revalidation.started", {"total": len(rows)})
    count = 0
    for row in rows:
        try:
            content = json.loads(row["content_json"])
            val_provider = row["validator_model"] or "openai"
            await _run_validators(run_id, row["component_id"], row["type"], content, val_provider, row["chapter_id"])
            count += 1
        except Exception as e:
            import logging
            logging.warning(f"[Revalidate] {row['type']} {row['chapter_id']}: {e}")

    await emit(run_id, "revalidation.completed", {"revalidated": count, "total": len(rows)})
    return {"revalidated": count}

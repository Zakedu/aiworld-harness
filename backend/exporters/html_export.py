"""
Material HTML Exporter — 학습자료를 고품질 HTML로 변환.

- 이모지 없는 타이포그래피 중심 레이아웃
- Bad/Good/Better 섹션 자동 파싱 → 카드 렌더링
- 체크리스트 자동 파싱 → 깔끔한 항목 렌더링
- 인쇄(PDF 저장) 최적화 CSS 포함
"""
from __future__ import annotations
import re
import html as _html
import json
import markdown as _md_lib
from ..db import get_conn


def _md(text: str) -> str:
    """마크다운 → HTML 변환 (표·볼드·이탤릭·코드 지원)."""
    return _md_lib.markdown(
        text or "",
        extensions=["tables", "nl2br", "fenced_code"],
        output_format="html",
    )

_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {
    --ink:        #1c1c1e;
    --mid:        #48484a;
    --light:      #f5f5f0;
    --accent:     #1d3557;
    --accent-mid: #457b9d;
    --bad:        #7c2d12;
    --good:       #14532d;
    --better:     #1e3a5f;
    --border:     #d1cfc8;
    --rule:       #e5e3dc;
    --print-bg:   white;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 14px;
    font-weight: 400;
    color: var(--ink);
    line-height: 1.85;
    background: var(--print-bg);
    max-width: 820px;
    margin: 0 auto;
    padding: 56px 48px 80px;
  }

  /* ── Print controls (hidden in PDF) ── */
  .print-bar {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-bottom: 36px;
  }
  .btn {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 12px;
    font-weight: 500;
    padding: 7px 18px;
    border: 1.5px solid var(--accent);
    border-radius: 4px;
    cursor: pointer;
    background: transparent;
    color: var(--accent);
    letter-spacing: 0.02em;
    transition: background 0.15s, color 0.15s;
  }
  .btn:hover { background: var(--accent); color: white; }
  .btn-solid { background: var(--accent); color: white; }
  .btn-solid:hover { background: #162840; }

  /* ── Document header ── */
  .doc-header {
    border-bottom: 1.5px solid var(--ink);
    padding-bottom: 24px;
    margin-bottom: 48px;
  }
  .chapter-meta {
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--mid);
    margin-bottom: 10px;
  }
  .chapter-title {
    font-family: 'Noto Serif KR', serif;
    font-size: 28px;
    font-weight: 700;
    line-height: 1.35;
    color: var(--ink);
  }
  .chapter-technique {
    margin-top: 10px;
    font-size: 13px;
    color: var(--mid);
    font-weight: 300;
    letter-spacing: 0.03em;
  }

  /* ── Section ── */
  .section { margin-bottom: 44px; }
  .section-label {
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--accent-mid);
    margin-bottom: 6px;
    font-weight: 500;
  }
  .section-heading {
    font-family: 'Noto Serif KR', serif;
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 16px;
    padding-left: 14px;
    border-left: 3px solid var(--accent);
    line-height: 1.4;
  }
  .section-body {
    color: var(--ink);
    white-space: pre-wrap;
    word-break: keep-all;
  }

  /* ── Background knowledge box ── */
  .bg-knowledge {
    background: var(--light);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-mid);
    padding: 18px 22px;
    font-size: 13px;
    line-height: 1.8;
    border-radius: 0 4px 4px 0;
  }
  .bg-knowledge-label {
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent-mid);
    font-weight: 600;
    margin-bottom: 8px;
  }

  /* ── Bad / Good / Better cards (code-editor style) ── */
  .bgb-grid { display: grid; gap: 16px; margin-top: 8px; }
  .bgb-card {
    border: 1px solid #3f3f46;
    border-radius: 6px;
    overflow: hidden;
    font-family: 'JetBrains Mono', monospace;
  }
  .bgb-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 10px 16px;
    background: #27272a;
    border-bottom: 1px solid #3f3f46;
  }
  .bgb-dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .bgb-sub { color: #71717a; font-weight: 400; margin-left: 2px; letter-spacing: 0; text-transform: none; }
  .bgb-bad    .bgb-header { color: #f87171; }
  .bgb-bad    .bgb-dot    { background: #f87171; }
  .bgb-good   .bgb-header { color: #4ade80; }
  .bgb-good   .bgb-dot    { background: #4ade80; }
  .bgb-better .bgb-header { color: #60a5fa; }
  .bgb-better .bgb-dot    { background: #60a5fa; }
  .bgb-body { padding: 16px 18px; font-size: 13px; line-height: 1.8; background: #09090b; color: #d4d4d8; white-space: pre-wrap; }

  /* ── Syntax tokens ── */
  .tok-keyword { color: #c084fc; }
  .tok-string  { color: #4ade80; }
  .tok-var     { color: #60a5fa; }
  .tok-bold    { color: #fbbf24; font-weight: 600; }

  /* ── Checklist ── */
  .checklist { list-style: none; margin-top: 4px; }
  .checklist li {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--rule);
    font-size: 13.5px;
    line-height: 1.6;
  }
  .checklist li:last-child { border-bottom: none; }
  .check-box {
    flex-shrink: 0;
    width: 16px;
    height: 16px;
    border: 1.5px solid var(--border);
    border-radius: 3px;
    margin-top: 3px;
    background: white;
  }

  /* ── Summary box ── */
  .summary-box {
    background: #fafafa;
    border-left: 4px solid #27272a;
    padding: 18px 22px;
    border-radius: 0 4px 4px 0;
    margin-top: 8px;
  }
  .summary-box p { font-size: 13.5px; line-height: 1.8; color: var(--ink); }

  /* ── Divider ── */
  .section-rule { border: none; border-top: 1px solid var(--rule); margin: 40px 0; }

  /* ── Footer ── */
  .doc-footer {
    margin-top: 64px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--mid);
    display: flex;
    justify-content: space-between;
  }

  /* ── Markdown rendered elements ── */
  .md-body p { margin-bottom: 0.7em; }
  .md-body p:last-child { margin-bottom: 0; }
  .md-body strong { font-weight: 600; color: var(--ink); }
  .md-body em { font-style: italic; }
  .md-body ul, .md-body ol { padding-left: 1.4em; margin: 0.4em 0 0.8em; }
  .md-body li { margin-bottom: 0.3em; line-height: 1.7; }
  .md-body code { font-family: 'JetBrains Mono', monospace; background: var(--code-bg); padding: 1px 6px; border-radius: 3px; font-size: 12px; }
  .md-body table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }
  .md-body th { background: var(--light); font-weight: 600; padding: 9px 14px; border: 1px solid var(--border); text-align: left; font-family: 'Noto Sans KR', sans-serif; }
  .md-body td { padding: 8px 14px; border: 1px solid var(--border); vertical-align: top; }
  .md-body tr:nth-child(even) td { background: #fafaf8; }
  .md-body blockquote { border-left: 3px solid var(--border); padding-left: 14px; color: var(--mid); margin: 12px 0; font-style: italic; }

  /* ── Print ── */
  @media print {
    .print-bar { display: none !important; }
    body { padding: 20px 24px; font-size: 13px; }
    .section-heading { font-size: 15px; }
    .bgb-grid { page-break-inside: avoid; }
    .bgb-card { page-break-inside: avoid; }
    .section { page-break-inside: avoid; }
    @page { margin: 20mm 18mm; }
  }
"""

_SECTION_LABELS: dict[str, str] = {
    "background_knowledge": "Background",
    "empathy_opener":        "Introduction",
    "concept":               "Core Concept",
    "example":               "Prompt Practice",
    "template":              "Applied Scenarios",
    "reflection":            "Review",
}


def _escape(text: str) -> str:
    return _html.escape(str(text or ""), quote=False)


def _render_example(body: str) -> str:
    """=== Bad/Good/Better (설명) === 블록을 코드 에디터 카드 HTML로 변환."""
    # [^=]* 로 확장 — '=== Bad (사람들이 많이 쓰는 방식) ===' 형태도 매칭
    parts = re.split(r"===\s*(Bad|Good|Better)[^=]*===", body, flags=re.IGNORECASE)
    if len(parts) < 2:
        return f'<div class="section-body">{_escape(body)}</div>'

    _sub = {"bad": "개선 전", "good": "기본 개선", "better": "권장 수준"}
    _css = {"bad": "bgb-bad", "good": "bgb-good", "better": "bgb-better"}

    cards = []
    i = 1
    while i < len(parts) - 1:
        label = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        key = label.lower()
        css = _css.get(key, "bgb-bad")
        sub = _sub.get(key, "")

        rendered_content = _tokenize_body(content)
        cards.append(f"""
        <div class="bgb-card {css}">
          <div class="bgb-header">
            <span class="bgb-dot"></span>
            {label.capitalize()}<span class="bgb-sub"> — {sub}</span>
          </div>
          <div class="bgb-body">{rendered_content}</div>
        </div>""")
        i += 2

    return f'<div class="bgb-grid">{"".join(cards)}</div>'


def _tokenize_body(text: str) -> str:
    """BGB 카드 본문 — 토큰 컬러링 (프롬프트:, 따옴표, [변수], **강조**)."""
    def _tok(line: str) -> str:
        s = _escape(line)
        s = re.sub(r"(프롬프트\s*[:：])", r"<span class='tok-keyword'>\1</span>", s)
        s = re.sub(r'"([^"]+)"', r'<span class=\'tok-string\'>&quot;\1&quot;</span>', s)
        s = re.sub(r"\[([^\]]+)\]", r"<span class='tok-var'>[\1]</span>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<span class='tok-bold'>\1</span>", s)
        return s

    return "\n".join(_tok(l) for l in text.split("\n"))


def _render_prompt_lines(text: str) -> str:
    """일반 섹션 본문용 — 산문은 마크다운, 프롬프트 줄은 코드블록."""
    lines = text.split("\n")
    prose_acc: list[str] = []
    prompt_acc: list[str] = []
    out: list[str] = []

    def flush_prose():
        if prose_acc:
            joined = "\n".join(prose_acc).strip()
            if joined:
                out.append(f'<div class="md-body">{_md(joined)}</div>')
            prose_acc.clear()

    def flush_prompt():
        if prompt_acc:
            joined = "\n".join(prompt_acc)
            out.append(f'<div class="prompt-block">{_escape(joined)}</div>')
            prompt_acc.clear()

    for line in lines:
        if re.match(r"^프롬프트\s*:", line):
            flush_prose()
            prompt_acc.append(re.sub(r"^프롬프트\s*:\s*", "", line))
        else:
            flush_prompt()
            prose_acc.append(line)

    flush_prose()
    flush_prompt()
    return "".join(out)


def _render_checklist(body: str) -> str:
    """- [ ] 항목을 체크리스트 HTML로 변환."""
    items = []
    for line in body.split("\n"):
        m = re.match(r"^\s*-\s*\[\s*\]\s*(.+)", line)
        if m:
            items.append(f'<li><span class="check-box"></span><span>{_escape(m.group(1))}</span></li>')
        elif line.strip():
            items.append(f'<li><span class="check-box"></span><span>{_escape(line.strip().lstrip("- "))}</span></li>')
    return f'<ul class="checklist">{"".join(items)}</ul>'


def _render_section(section: dict, idx: int, total: int) -> str:
    kind = section.get("kind", "")
    heading = re.sub(r"^[\U0001F300-\U0001FFFF\s]+", "", section.get("heading", "")).strip()
    body = section.get("body", "")
    label = _SECTION_LABELS.get(kind, "")

    label_html = f'<div class="section-label">{_escape(label)}</div>' if label else ""

    if kind == "background_knowledge":
        content_html = f"""
        <div class="bg-knowledge">
          <div class="bg-knowledge-label">사전 지식</div>
          <div class="md-body">{_md(body)}</div>
        </div>"""
    elif kind == "example":
        content_html = _render_example(body)
    elif kind == "reflection" and ("체크리스트" in heading or "[ ]" in body):
        content_html = _render_checklist(body)
    elif kind == "reflection":
        content_html = f'<div class="summary-box md-body">{_md(body)}</div>'
    elif kind == "template":
        content_html = f'<div class="section-body">{_render_prompt_lines(body)}</div>'
    else:
        content_html = f'<div class="section-body md-body">{_md(body)}</div>'

    rule = '<hr class="section-rule">' if idx < total - 1 else ""
    return f"""
    <div class="section">
      {label_html}
      <h2 class="section-heading">{_escape(heading)}</h2>
      {content_html}
    </div>
    {rule}"""


def build_material_html(run_id: str, chapter_id: str) -> str:
    with get_conn() as conn:
        comp = conn.execute(
            "SELECT content_json FROM components WHERE run_id=? AND type='material' AND chapter_id=? ORDER BY version DESC LIMIT 1",
            (run_id, chapter_id),
        ).fetchone()
        bp = conn.execute(
            "SELECT content_json FROM blueprints WHERE run_id=? ORDER BY version DESC LIMIT 1",
            (run_id,),
        ).fetchone()

    if not comp:
        raise ValueError(f"material not found: run={run_id} chapter={chapter_id}")

    material = json.loads(comp["content_json"])
    blueprint = json.loads(bp["content_json"]) if bp else {}

    curriculum = blueprint.get("curriculum", [])
    chapter_info = next((c for c in curriculum if c.get("chapter_id") == chapter_id), {})
    chapter_name = chapter_info.get("chapter_name", chapter_id)
    technique = chapter_info.get("prompt_technique", "")
    course_name = blueprint.get("course_name", "")

    sections = material.get("sections", [])
    sections_html = "".join(
        _render_section(s, i, len(sections)) for i, s in enumerate(sections)
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape(chapter_id)} — {_escape(chapter_name)}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="print-bar">
    <button class="btn" onclick="window.close()">닫기</button>
    <button class="btn btn-solid" onclick="window.print()">PDF 저장</button>
  </div>

  <header class="doc-header">
    <div class="chapter-meta">{_escape(course_name)} &nbsp;·&nbsp; Chapter {_escape(chapter_id)}</div>
    <h1 class="chapter-title">{_escape(chapter_name)}</h1>
    <div class="chapter-technique">핵심 기법 &nbsp;— &nbsp;{_escape(technique)}</div>
  </header>

  <main>{sections_html}</main>

  <footer class="doc-footer">
    <span>AI World</span>
    <span>{_escape(chapter_id)} · {_escape(chapter_name)}</span>
  </footer>
</body>
</html>"""

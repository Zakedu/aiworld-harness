from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RuntimeRegressionTests(unittest.TestCase):
    def test_favicon_request_does_not_404(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/favicon.ico")

        self.assertLess(response.status_code, 400)

    def test_run_list_fetch_rejects_non_array_responses(self):
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

        self.assertIn("if (!Array.isArray(runs))", html)
        self.assertIn("Run 목록 응답 형식이 올바르지 않습니다", html)

    def test_run_script_uses_env_port_and_falls_forward_on_conflict(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")

        self.assertIn("ENV_PORT", run_sh)
        self.assertIn("port_in_use()", run_sh)
        self.assertIn("선택한 포트가 사용 중이라", run_sh)

    def test_practice_title_policy_is_consistent_across_ui_and_prompt(self):
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        prompt = (ROOT / "backend" / "agents" / "practice_generator.py").read_text(encoding="utf-8")

        self.assertIn("위인명·단계명 접두 없음", html)
        self.assertNotIn("item:'{위인} + 단계 포함'", html)
        self.assertIn("- 콘텐츠명(title): **40~100자**", prompt)
        self.assertIn("- 문제(question): **40~100자**", prompt)

    def test_github_validation_workflow_exists(self):
        workflow = ROOT / ".github" / "workflows" / "validate.yml"

        self.assertTrue(workflow.exists())
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("python -m compileall backend", text)
        self.assertIn("yaml.safe_load", text)
        self.assertIn("json.loads", text)

    def test_material_pdf_export_css_matches_main_design_spec(self):
        from backend.exporters.html_export import _CSS

        self.assertIn("font-size: 15px;", _CSS)
        self.assertIn("font-size: 14px;", _CSS)
        self.assertIn("print-color-adjust: exact", _CSS)
        self.assertIn(".bgb-bad    .bgb-header { background: #fdf2f2; color: #b91c1c; }", _CSS)
        self.assertIn(".bgb-good   .bgb-header { background: #f1f8f3; color: #15803d; }", _CSS)
        self.assertIn(".bgb-better .bgb-header { background: #f1f4fb; color: #1d4ed8; }", _CSS)
        self.assertIn(".bgb-body { padding: 16px 18px; font-size: 14px;", _CSS)
        self.assertIn(".section-heading    { break-after: avoid; page-break-after: avoid; }", _CSS)
        self.assertIn(".bgb-card     { break-inside: avoid; page-break-inside: avoid; }", _CSS)
        self.assertNotIn("background: #09090b", _CSS)
        self.assertNotIn(".bgb-grid { page-break-inside: avoid;", _CSS)
        self.assertNotIn(".section { page-break-inside: avoid;", _CSS)

    def test_anthropic_low_credit_error_falls_back_to_openai(self):
        from backend.agents.base import _should_fallback

        class LowCreditError(Exception):
            status_code = 400

        err = LowCreditError(
            "Your credit balance is too low to access the Anthropic API. "
            "Please go to Plans & Billing to upgrade or purchase credits."
        )

        self.assertTrue(_should_fallback(err))

    def test_env_file_values_take_priority_over_process_environment(self):
        config = (ROOT / "backend" / "config.py").read_text(encoding="utf-8")

        self.assertIn("load_dotenv(ROOT / \".env\", override=True)", config)

    def test_run_detail_hides_missing_components_while_generating(self):
        from backend.main import _missing_components_for_response

        with patch(
            "backend.main.orchestrator.find_recoverable_components_for_run",
            return_value=[{"chapter_id": "1-1", "type": "quiz"}],
        ) as find_recoverable:
            self.assertEqual(_missing_components_for_response("generating", "run-1"), [])
            find_recoverable.assert_not_called()

        with patch(
            "backend.main.orchestrator.find_recoverable_components_for_run",
            return_value=[{"chapter_id": "1-1", "type": "quiz"}],
        ):
            self.assertEqual(
                _missing_components_for_response("generation_incomplete", "run-1"),
                [{"chapter_id": "1-1", "type": "quiz"}],
            )

    def test_recoverable_component_query_has_single_order_by_clause(self):
        orchestrator = (ROOT / "backend" / "orchestrator.py").read_text(encoding="utf-8")

        self.assertNotIn(
            "ORDER BY version DESC LIMIT 1\n                    ORDER BY version DESC LIMIT 1",
            orchestrator,
        )

    def test_material_export_renders_loose_markdown_tables(self):
        from backend.exporters.html_export import _md

        html = _md(
            """
| 요소 | 무엇 | 예시 |

|---|---|---|

| Context(상황) | 응답이 발생한 생활 장면 | 출근길에 앱 알림을 확인하는 순간 |

| Behavior(행동) | 관찰하려는 실제 사용 행동 | 알림을 끄거나 앱을 삭제한 행동 |
""".strip()
        )

        self.assertIn("<table>", html)
        self.assertIn("<th>요소</th>", html)
        self.assertIn("<td>Context(상황)</td>", html)
        self.assertNotIn("|---|---|---|", html)


if __name__ == "__main__":
    unittest.main()

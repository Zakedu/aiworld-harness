from __future__ import annotations

import pathlib
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()

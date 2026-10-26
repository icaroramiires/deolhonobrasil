"""
Tests for SPEC-0019 — Frontend Civic UI, Unified Design System & Traceable Evidences.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestCivicUIAndDesignSystem(unittest.TestCase):
    """Verifies Civic UI compliance with docs/design/ handoff package."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage = CivicLakehouseStorage(data_dir=Path(self.tmp_dir.name))
        self.service = CivicAuditAPIService(
            storage=self.storage,
            admin_token="secret-admin-token-test-spec0019-32bytes",
        )
        self.app = CivicAuditHTTPApp(self.service)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _get_html(self) -> str:
        resp = self.app.handle_request(method="GET", path="/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "text/html; charset=utf-8")
        self.assertIsNotNone(resp.raw_html)
        return resp.raw_html or ""

    def test_ui_serves_html_with_design_tokens_and_theme_support(self) -> None:
        """AC-074: Verify HTML includes design tokens, Manrope/DM Sans typography, and dark theme support."""
        html = self._get_html()

        # 1. Typography
        self.assertIn("Manrope", html)
        self.assertIn("DM Sans", html)

        # 2. Institutional Colors (docs/design/design-tokens.json)
        # Deep green brand: #12654c, lime accent: #d3f05b
        self.assertTrue(
            "#12654c" in html.lower() or "18, 101, 76" in html,
            "Expected institutional deep green brand color #12654c in CSS tokens",
        )
        self.assertTrue(
            "#d3f05b" in html.lower() or "211, 240, 91" in html,
            "Expected lime accent color #d3f05b in CSS tokens",
        )

        # 3. Dark Mode Support & Persistence
        self.assertIn('data-theme="dark"', html)
        self.assertTrue(
            "#0e1714" in html.lower() or "#14201c" in html.lower(),
            "Expected dark background/surface color from design tokens",
        )
        self.assertIn("theme-toggle", html)
        self.assertIn("localStorage", html)

    def test_ui_renders_seven_navigation_views_and_search_shortcut(self) -> None:
        """AC-075: Verify 7 navigation views and Ctrl/Cmd+K search shortcut."""
        html = self._get_html()

        # 7 Main Navigation items (docs/design/information-architecture.md & screens.md)
        expected_views = [
            "inicio",
            "pesquisa",
            "despesas",
            "contratos",
            "analises",
            "evidencias",
            "acompanhamentos",
        ]

        for view in expected_views:
            pattern = re.compile(rf'(data-nav="{view}"|data-view="{view}"|id="view-{view}")', re.IGNORECASE)
            self.assertTrue(
                pattern.search(html),
                f"Expected navigation view '{view}' in UI HTML markup",
            )

        # Search shortcut (Ctrl+K / Cmd+K)
        self.assertTrue(
            "key === 'k'" in html or 'key === "k"' in html or 'key === "K"' in html or "ctrlkey" in html.lower(),
            "Expected Ctrl+K / Cmd+K global search shortcut implementation in script",
        )
        self.assertIn('id="global-search"', html)

    def test_ui_enforces_epistemic_badges_and_non_accusatory_language(self) -> None:
        """AC-076 & AC-077: Verify epistemic classifications, AI limit banner, and non-accusatory language."""
        html = self._get_html()

        # Epistemic classification badges (docs/design/design-system.md)
        self.assertIn("Fato documentado", html)
        self.assertIn("Divergência", html)
        self.assertIn("Padrão incomum", html)
        self.assertIn("Hipótese", html)
        self.assertIn("Revisado", html)

        # AI banner mandatory text (docs/design/screens.md)
        self.assertTrue(
            "ia apoia, pessoas verificam" in html.lower()
            or "ia apoia, auditores verificam" in html.lower(),
            "Expected mandatory AI limitation banner 'IA apoia, pessoas verificam'",
        )

        # Epistemic 3 layers
        self.assertIn("[DADO OFICIAL]", html)
        self.assertIn("[INFERÊNCIA ESTATÍSTICA]", html)
        self.assertIn("[LIMITAÇÃO E HIPÓTESE]", html)

        # Non-accusatory language rule
        assert_non_accusatory_language(html)

    def test_ui_handles_loading_empty_and_error_states(self) -> None:
        """Verify UI provides markup/components for all 6 required interaction states."""
        html = self._get_html()

        required_state_indicators = [
            "skeleton",         # Loading state
            "empty",            # Zero results / empty
            "error",            # Recoverable / permanent error
            "incompleto",       # Incomplete data indicator
            "indisponível",     # Source unavailable indicator
            "sem permissão",    # RLS permission denied
        ]

        html_lower = html.lower()
        for state in required_state_indicators:
            self.assertIn(
                state,
                html_lower,
                f"Expected state indicator '{state}' in UI template markup",
            )


if __name__ == "__main__":
    unittest.main()

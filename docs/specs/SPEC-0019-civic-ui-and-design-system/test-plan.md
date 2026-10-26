# Test Plan — SPEC-0019

## Test Matrix & Anchors

| Requirement | Test Anchor | Description |
| :--- | :--- | :--- |
| `FR-040`, `AC-074` | `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_serves_html_with_design_tokens_and_theme_support` | Verifies that the UI serves HTML embedding design tokens, typography, and light/dark theme support. |
| `FR-041`, `AC-075` | `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_renders_seven_navigation_views_and_search_shortcut` | Confirms rendering of all 7 navigation views and keyboard shortcuts. |
| `FR-042`, `SEC-022`, `AC-077` | `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_enforces_epistemic_badges_and_non_accusatory_language` | Validates epistemic separation badges and non-accusatory language rules. |
| `NFR-022`, `AC-076` | `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_handles_loading_empty_and_error_states` | Tests responsive viewports and state handlers (loading, empty, error). |

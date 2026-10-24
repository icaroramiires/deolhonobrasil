# Subagent & Model Routing Policy (Token Economy)

Always delegate tasks to the most specific subagent using the lightest capable model (`flash_lite`, `flash`, or `pro`) when calling `invoke_subagent`:

1. **`Model: "flash_lite"`** — Use for:
   - `donb-compliance-linter`: Non-accusatory lexical checks, LGPD CPF masking verification, static lint runs (`lint.mjs --app`).
   - `donb-portal-scout` / `docs-lookup`: Government portal schema lookups (`CGU`, `PNCP`, `CEAP`, `CEAPS`), file discovery, metadata extraction.
   - `doc-updater` / `comment-analyzer`: Documentation updates, README sync, docstring checks.

2. **`Model: "flash"`** — Use for:
   - `donb-etl-builder`: Implementing data connectors, SQLite/DuckDB/Parquet storage, quarantine, and financial reconciliation.
   - `donb-ui-builder`: Implementing UI screens and SVG charts under `.taste-skill/direction.json` (`achromatic-ledger`).
   - `donb-browser-qa` / `e2e-runner`: Running `agent-browser` (`open`, `snapshot -i`, `@eN`) and `inspect.mjs --app`.
   - `tdd-guide` / `build-error-resolver` / `code-explorer` / `code-simplifier`: Writing unit tests, fixing build/type errors, exploring modules.

3. **`Model: "pro"`** — Reserve strictly for:
   - `donb-audit-ai-architect`: Statistical anomaly formulas (`Z-Score`, `Benford`, `HHI`), `Laya` System 1 Decision Engine (`Choice`/`Score`/`Noul`), grounded RAG, and 3-layer epistemic rules.
   - `security-reviewer` / `python-reviewer` / `database-reviewer` / `architect`: Security audits, indirect prompt-injection defense, PostgreSQL RLS policies, and checkpoint gate reviews.

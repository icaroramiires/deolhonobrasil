# Technical Design Plan — SPEC-0019

## Architecture Overview
The civic UI is served directly through the WSGI application (`CivicAuditHTTPApp`), providing an offline-first single-page application experience backed by structured API endpoints (`/api/v1/...`).

## Component Breakdown
1. **Design System Engine:** CSS variables injected from `docs/design/design-tokens.json`, supporting light and dark themes.
2. **Router & Views:** Client-side view manager handling the 7 navigation views (Overview, Search, Expenses, Contracts, Analyses, Evidences, Watchlists).
3. **API Client:** Fetch-based wrapper interacting with WSGI routes (`/api/v1/dossiers`, `/api/v1/expenses`, etc.).
4. **State Management & Assertions:** Runtime validation of reconciliations (`console.assert`) and non-accusatory guardrails.

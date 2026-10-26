# Technical Design Plan: SPEC-0020

## 1. Architecture Overview
- Implementation of Python dataclasses for `CivicEntityProfile`, `ContractTimelineEvent`, and `ExpenseDetailPayload`.
- Extension of `CivicAuditHTTPApp` WSGI handlers to serve JSON detail payloads and HTML profile views.
- Integration with frontend modal controllers in `wireframe_de_olho_no_brasil.html` adhering to WCAG 2.2 AA.

## 2. Component Design
- **Endpoints:** `/api/v1/entities/{id}`, `/api/v1/expenses/{id}`, `/api/v1/contracts/{id}`.
- **Frontend Components:** Modal dialogs with focus trap and `Esc` key listeners.

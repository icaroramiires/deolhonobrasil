# Data Model & State Contracts — SPEC-0019

## Design Tokens (`design-tokens.json`)
- **Primary Color:** `#12654c` (Deep Green)
- **Accent Color:** `#d3f05b` (Lime)
- **Light Theme Background:** `#f5f7f6` / `#ffffff`
- **Dark Theme Background:** `#0e1714` / `#14201c`
- **Typography:** Manrope, DM Sans, monospace for SHA-256 hashes.

## UI State Contract
- `activeView`: `overview` | `search` | `expenses` | `contracts` | `analyses` | `evidences` | `watchlists`
- `theme`: `light` | `dark`
- `filterState`: object containing search query, date ranges, status filters.
- `epistemicBadge`: `DADO OFICIAL` | `INFERÊNCIA ESTATÍSTICA` | `HIPÓTESE DE AUDITORIA`

# Technical Design Plan — SPEC-0018

## Architecture & Implementation
- **Rule Function:** `evaluate_sanctioned_partner_supplier_rule` (`R-CROSS-SANCTIONED-PARTNER`) in `deolhonobrasil.engine.rules.sanctioned_partner`.
- **Inputs:** `CuratedPublicContract` / `CuratedPublicExpense`, list of `CuratedCorporateMemberRecord` (QSA), list of `CuratedSanctionRecord` (CEIS/CNEP).
- **Complexity:** $O(N + M)$ temporal matching with hash-based indexing and set lookups.
- **Provenance:** SHA-256 combination of sanction hash, QSA member hash, and contract/expense hash.

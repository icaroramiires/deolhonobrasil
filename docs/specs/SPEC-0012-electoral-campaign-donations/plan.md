# Technical Design Plan: SPEC-0012

## 1. Architecture & Components
- **Model:** `CuratedElectoralDonation` (`frozen=True`) with fields for donor identification, candidate/mandatary ID, amount, election year, and SHA-256 provenance hash.
- **Rule Function:** `evaluate_electoral_donor_supplier_crossmatch_rule` (`R-CROSS-ELECTORAL-DONOR-SUPPLIER`), accepting curated public expenses and electoral donations, filtering out CPF homonyms, and emitting an `AuditSignal` with dual SHA-256 provenance.

## 2. Implementation Steps
1. Implement `CuratedElectoralDonation` in `src/deolhonobrasil/models/electoral.py`.
2. Implement `evaluate_electoral_donor_supplier_crossmatch_rule` in `src/deolhonobrasil/audit/rules/electoral_crossmatch.py`.
3. Add unit tests in `tests/test_electoral_campaign_donations.py` matching the 4 test anchors.

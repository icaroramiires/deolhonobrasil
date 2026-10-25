# Technical Design & Plan — SPEC-0013

## Architecture & Components
1. **Model:** `CuratedCorporateMemberRecord` (`frozen=True`) representing QSA items from `OfficialSource.RECEITA_FEDERAL_CNPJ`.
2. **Rules Engine Functions:**
   - `evaluate_qsa_shared_partner_rule`
   - `evaluate_qsa_individual_donor_rule`
3. **Provenance & Hashing:** SHA-256 natural key composition combining CNPJ, partner CPF hash, and qualification code.

## File Locations
- Model & Rules: `src/deolhonobrasil/rules/qsa_crossmatch.py`
- Tests: `tests/test_qsa_and_corporate_members.py`

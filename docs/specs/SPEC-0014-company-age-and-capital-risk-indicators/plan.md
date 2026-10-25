# Technical Design Plan — SPEC-0014

## Architecture & Components
1. **Model (`CuratedCompanyRegistrationRecord`)**:
   - Located in `deolhonobrasil.models.company` (or corresponding domain module).
   - Attributes: `cnpj`, `company_name`, `opening_date` (datetime.date), `share_capital_brl` (Decimal), `status`, `provenance_sha256`.
2. **Audit Rules**:
   - `evaluate_recent_company_creation_rule(record, contract_amount, contract_date)`
   - `evaluate_low_capital_outlier_rule(record, contract_amount)`
3. **Integration**:
   - Plug into the audit evaluation pipeline (`Laya` or batch verification runner).

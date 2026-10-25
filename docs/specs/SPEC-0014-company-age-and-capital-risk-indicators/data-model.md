# Data Model Specification — SPEC-0014

## CuratedCompanyRegistrationRecord
- `cnpj`: `str` (Format: `XX.XXX.XXX/XXXX-XX`)
- `company_name`: `str`
- `opening_date`: `datetime.date`
- `share_capital_brl`: `Decimal`
- `status`: `str`
- `provenance_sha256`: `str` (SHA-256 hash of raw upstream payload)

## Audit Signal Output
- `rule_id`: `str` (`R-CORP-RECENT-CREATION` or `R-CORP-LOW-CAPITAL-OUTLIER`)
- `severity`: `str` / `float`
- `details`: `dict` containing calculated age in days, capital ratio, and non-accusatory disclaimer.

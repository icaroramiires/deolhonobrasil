# Technical Design Plan — SPEC-0007

## Components & Modules
1. **`CuratedSanctionRecord` (`src/deolhonobrasil/models/sanction.py`):**
   - Immutably frozen dataclass (`frozen=True`) representing curated sanctions from CGU CEIS/CNEP.
   - Includes `ProvenanceMetadata`, `payload_sha256`, masked CPF/CNPJ, and date ranges.

2. **`parse_cgu_ceis_cnep_json_batch` (`src/deolhonobrasil/etl/sanctions_connector.py`):**
   - Batch parser validating schema, computing SHA-256 hashes, masking CPFs, and routing invalid rows to quarantine.

3. **Deterministic Rules (`src/deolhonobrasil/rules/cross_sanctions.py`):**
   - `evaluate_ceis_cnep_sanctioned_supplier_rule` (`R-CROSS-CEIS-SANCTIONED-SUPPLIER`): Cross-references active CNPJ sanctions against contracts.
   - `evaluate_amendment_execution_divergence_rule` (`R-CROSS-AMENDMENT-EXECUTION-GAP`): Detects financial gaps between amendments and execution reports.

4. **API Endpoint (`src/deolhonobrasil/api/endpoints/sanctions.py`):**
   - FastAPI route `GET /api/v1/sanctions` with pagination, filtering, and public reader access.

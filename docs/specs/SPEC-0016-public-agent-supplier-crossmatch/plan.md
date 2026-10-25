# Technical Design (Plan) — SPEC-0016

## Architecture Overview
This technical plan specifies the components needed to implement `SPEC-0016`:
1. **`CuratedPublicAgentRecord` Model:** Frozen Pydantic model representing public servants with masked CPF, organ code/name, and SHA-256 provenance hash.
2. **`evaluate_public_agent_supplier_crossmatch_rule` Rule Engine Function (`R-CROSS-PUBLIC-AGENT-SUPPLIER`):** Crosses agent records against contract/expense suppliers' QSA members, filtering by exact organ matching and emitting `AuditSignal` objects.

## Components & File Layout
- `src/deolhonobrasil/models/public_agent.py`: Pydantic definitions for public agents.
- `src/deolhonobrasil/rules/public_agent_supplier_crossmatch.py`: Implementation of `evaluate_public_agent_supplier_crossmatch_rule`.
- `tests/test_public_agent_supplier_crossmatch.py`: Comprehensive test suite corresponding to the 4 required test anchors.

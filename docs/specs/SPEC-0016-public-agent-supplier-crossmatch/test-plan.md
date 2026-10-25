# Test Plan — SPEC-0016

## Test Mapping
- `FR-034` / `DATA-018` / `AC-062` $\rightarrow$ `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_model_validation_and_masking`
- `FR-035` / `AC-063` $\rightarrow$ `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_detects_conflict_in_same_organ`
- `AC-064` $\rightarrow$ `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_ignores_different_organ`
- `NFR-019` / `AC-065` $\rightarrow$ `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_ignores_unrelated_members`

## Execution Command
```bash
PYTHONPATH=src pytest tests/test_public_agent_supplier_crossmatch.py -v
```

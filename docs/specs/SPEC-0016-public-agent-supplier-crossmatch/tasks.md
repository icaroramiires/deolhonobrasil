# Tasks (`TASK-1601` to `TASK-1604`) — Jira DONB-23

- [ ] **`TASK-1601`**: Implement `CuratedPublicAgentRecord` model with `frozen=True`, CPF masking validation (`***.XXX.XXX-**`), and SHA-256 provenance calculation (`DATA-018`, `FR-034`, `AC-062`).
- [ ] **`TASK-1602`**: Implement `evaluate_public_agent_supplier_crossmatch_rule` (`R-CROSS-PUBLIC-AGENT-SUPPLIER`) supporting same-organ matching with QSA partners and expense/contract records (`FR-035`, `AC-063`, `AC-064`, `AC-065`).
- [ ] **`TASK-1603`**: Ensure anti-homonímia safeguards (`NFR-019`) and non-accusatory language disclaimer (`SEC-019`) are embedded in signal metadata.
- [ ] **`TASK-1604`**: Write comprehensive test suite in `tests/test_public_agent_supplier_crossmatch.py` covering all 4 mandated test anchors.

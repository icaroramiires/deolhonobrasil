# Test Plan: SPEC-0001 — Pipeline de Dados Públicos

## Mapeamento de Requisitos para Testes
Todos os requisitos funcionais, de segurança e de dados do SPEC-0001 são cobertos pelos 11 métodos de teste definidos em `tests/test_foundation_and_pipeline.py`.

### Test Anchors Executados
1. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_valid_cnpj_and_invalid_cnpj`
2. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_cpf_lgpd_masking_on_normalization`
3. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_already_masked_cgu_cpf_is_preserved`
4. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_missing_monetary_value_never_becomes_zero`
5. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_prompt_injection_and_control_chars_sanitization`
6. `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_editorial_policy_blocks_accusatory_language`
7. `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_camara_ceap_connector_validates_and_quarantines`
8. `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_senado_ceaps_connector_validates_and_quarantines_missing_amount`
9. `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_cgu_amendments_and_pncp_contracts_connectors`
10. `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_lakehouse_idempotency_and_reconciliation`
11. `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_end_to_end_cli_sample_pipeline`

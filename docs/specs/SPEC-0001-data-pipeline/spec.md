# SPEC-0001 — Pipeline de Dados Públicos, Proveniência SHA-256 e Reconciliação Contábil

## 1. Identificador e Título
- **ID:** SPEC-0001
- **Título:** Pipeline de Dados Públicos, Proveniência SHA-256 e Reconciliação Contábil
- **Subsistema:** Core Ingestion & Lakehouse Pipeline

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0
- **Data:** 2026-10-23

## 3. Problema e Motivação
Os portais de transparência públicos brasileiros (Câmara dos Deputados, Senado Federal, CGU, PNCP) expõem dados fragmentados, com frequentes inconsistências monetárias, ausência de rastreabilidade de hash bruto e riscos de contaminação por dados corrompidos ou ataques de injeção indireta. O sistema **De Olho no Brasil** exige um pipeline robusto, idempotente e estritamente auditável que garanta proveniência criptográfica (`SHA-256`), mascaramento de LGPD, vedação a valores nulos convertidos em zero e reconciliação contábil exata.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Ingerir dados de CEAP, CEAPS, Emendas Parlamentares e Contratos PNCP.
- Garantir proveniência com hash SHA-256 do payload bruto.
- Isolar registros inválidos ou corrompidos em Quarentena.
- Impor reconciliação financeira exata utilizando aritmética de ponto flutuante de precisão (`Decimal`).

### Não-Objetivos
- Análise estatística avançada de desvios (atribuída ao SPEC-0002).
- Geração de narrativas via LLM (atribuída ao SPEC-0002).

## 5. Atores e Permissões
- **Orquestrador de ETL:** Executa tarefas de ingestão agendadas via CLI ou background workers.
- **Auditor Humano:** Acessa registros curados e relatórios de reconciliação.

## 6. Fluxos Principais
1. **Extração:** Coleta de dados brutos das fontes governamentais.
2. **Hash e Normalização:** Cálculo do SHA-256 e limpeza de caracteres de controle / prompt injection.
3. **Validação e Quarentena:** Se o registro possui valores obrigatórios ausentes ou CNPJ/CPF inválidos, é enviado para a Quarentena.
4. **Curadoria e Reconciliação:** Gravação na camada Curated e emissão de `BatchReconciliationReport`.

## 7. Cenários Alternativos e de Erro
- **Payload Corrompido / Ausente:** O registro é rejeitado para a tabela/diretório de quarentena com motivo documentado, sem interromper o lote.
- **Valores Monetários Nulos:** Tratados explicitamente como nulos, **nunca** convertidos em zero (prevenção de distorção contábil).

## 8. Requisitos Funcionais
- **FR-001:** O sistema deve conectar-se às fontes CEAP, CEAPS, CGU e PNCP.
- **FR-002:** O sistema deve calcular e persistir o hash `SHA-256` de cada payload bruto recebido.
- **FR-003:** O sistema deve validar chaves fiscais (CNPJ) e isolar registros inválidos em Quarentena.
- **FR-004:** O sistema deve emitir um relatório de reconciliação de lote (`BatchReconciliationReport`) garantindo centavo a centavo.

## 9. Requisitos Não Funcionais
- **NFR-001:** Idempotência estrita em reexecuções de lote (mesmo hash/payload não duplica registros curados).
- **NFR-002:** Uso obrigatório de `Decimal` para valores monetários.

## 10. Regras de Negócio
- **DATA-001:** Proibição absoluta de converter valor monetário nulo em zero (`None` permanece `None`).
- **DATA-002:** Idempotência baseada em hash de proveniência.
- **DATA-003:** Reconciliação exata entre a soma dos itens e o total do lote utilizando `Decimal`.

## 11. Requisitos de Segurança e Privacidade
- **SEC-001:** Mascaramento LGPD automático de CPFs de pessoas físicas comuns no formato `***.XXX.XXX-**`.
- **SEC-002:** Sanitização rigorosa contra prompt injection indireto e remoção de caracteres de controle invisíveis.

## 12. Critérios de Aceite
- **AC-001:** Ingestão de CEAP valida e separa quarentena corretamente.
- **AC-002:** CPFs são mascarados para `***.XXX.XXX-**`.
- **AC-003:** Valores monetários ausentes não viram zero.
- **AC-004:** Sanitização remove tags de prompt injection.
- **AC-005:** Reconciliação do lakehouse fecha perfeitamente.

## 13. Dependências
- Python 3.10+, Pydantic v2, pytest.

## 14. Riscos e Limitações
- Indisponibilidade temporária de APIs governamentais (mitigada por retry com backoff e quarentena de falhas de rede).

## 15. Estratégia de Testes
### Test Anchors
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_valid_cnpj_and_invalid_cnpj`
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_cpf_lgpd_masking_on_normalization`
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_already_masked_cgu_cpf_is_preserved`
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_missing_monetary_value_never_becomes_zero`
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_prompt_injection_and_control_chars_sanitization`
- `tests/test_foundation_and_pipeline.py::TestFoundationPrivacyAndLGPD::test_editorial_policy_blocks_accusatory_language`
- `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_camara_ceap_connector_validates_and_quarantines`
- `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_senado_ceaps_connector_validates_and_quarantines_missing_amount`
- `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_cgu_amendments_and_pncp_contracts_connectors`
- `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_lakehouse_idempotency_and_reconciliation`
- `tests/test_foundation_and_pipeline.py::TestConnectorsAndLakehousePipeline::test_end_to_end_cli_sample_pipeline`

## 16. Questões Pendentes
Nenhuma questão bloqueante pendente.

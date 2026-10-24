# SPEC-0002 — Regras Determinísticas de Auditoria, Estatística, Motor Laya System 1 e Grounded RAG

## 1. Identificador e Título
- **ID:** SPEC-0002
- **Título:** Regras Determinísticas de Auditoria, Estatística, Motor Laya System 1 e Grounded RAG
- **Subsistema:** Audit Engine, Statistical Analysis & AI Narrator

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0
- **Data:** 2026-10-23

## 3. Problema e Motivação
Detectar desvios, superfaturamento e anomalias em gastos públicos exige rigor estatístico rigoroso (Z-Score paramétrico/não-paramétrico, HHI, Lei de Benford) aliado a um motor de decisão automatizado (*System 1* `Laya`) e a um gerador de narrativas fundamentado (`GroundedDossierNarrator`) que evite alucinações e proíba terminologia acusatória.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Implementar testes estatísticos robustos para desvios de cotas e contratos.
- Aplicar regras determinísticas de auditoria garantindo linguagem não-acusatória.
- Orquestrar o motor `LayaSystem1Adapter` com roteamento obrigatório para revisão humana quando a severidade for alta.
- Gerar dossiês em 3 blocos epistêmicos estritos vinculados a hashes de proveniência.

### Não-Objetivos
- Ingestão direta de APIs (atribuída ao SPEC-0001).

## 5. Atores e Permissões
- **Sistema de Auditoria Automática:** Executa rotinas estatísticas e de regras.
- **Analista Humano:** Revisa decisões de alta severidade do motor Laya.

## 6. Fluxos Principais
1. **Análise Estatística:** Cálculo de Z-Score, HHI e Benford sobre os dados curados.
2. **Avaliação de Regras Determinísticas:** Identificação de sinais de auditoria (ex: sobrepreço, concentração de fornecedores).
3. **Decisão Laya (System 1):** Classificação de severidade e roteamento (ex: score >= 0.70 exige `REVISAO_HUMANA`).
4. **Narrativa Grounded:** Construção do dossiê com os 3 blocos epistêmicos obrigatórios e verificação de hashes.

## 7. Cenários Alternativos e de Erro
- **Ausência de Proveniência:** O narrador recusa estritamente gerar o dossiê se faltarem hashes de rastreabilidade.
- **Falsos Positivos Estatísticos:** Mitigados por limiares calibrados e revisão humana obrigatória.

## 8. Requisitos Funcionais
- **FR-005:** O sistema deve calcular Z-Score (paramétrico e MAD), índice HHI de concentração e conformidade com a Lei de Benford.
- **FR-006:** O sistema deve avaliar regras determinísticas de auditoria de sobrepreço e concentração.
- **FR-007:** O motor `LayaSystem1Adapter` deve classificar severidade e impor revisão humana para scores elevados, sem nunca auto-publicar acusações nominais.

## 9. Requisitos Não Funcionais
- **NFR-003:** Tempo de resposta determinístico para análises estatísticas em lote.
- **NFR-004:** Separação estrita entre dado oficial, inferência estatística e hipótese de auditoria.

## 10. Regras de Negócio e Dados
- **DATA-004:** Modelagem de sinais de auditoria estruturados (`AuditSignal`).
- **AI-001:** Calibração rigorosa do `LayaSystem1Adapter`.
- **AI-002:** Severidade estatística alta (score >= 0.70) obrigatoriamente roteada para `REVISAO_HUMANA`.
- **AI-003:** `GroundedDossierNarrator` gera exatamente 3 blocos epistêmicos e recusa qualquer síntese sem `provenance_hashes`.

## 11. Requisitos de Segurança e Privacidade
- **SEC-003:** Bloqueio estrito de termos acusatórios e isolamento contra alucinação de LLM.

## 12. Critérios de Aceite
- **AC-006:** Cálculos de Z-Score e Benford retornam métricas corretas.
- **AC-007:** Regras de sobrepreço e concentração geram sinais válidos e não acusatórios.
- **AC-008:** Laya System 1 roteia severidades altas para revisão humana.
- **AC-009:** Narrador RAG gera blocos epistêmicos e recusa payloads vazios de proveniência.

## 13. Dependências
- SPEC-0001 (Dados Curados e Lakehouse).

## 14. Riscos e Limitações
- Risco de alarmes falsos em desvios estatísticos atípicos (mitigado pelo pipeline de triagem humana).

## 15. Estratégia de Testes
### Test Anchors
- `tests/test_audit_and_governance.py::TestAuditStatistics::test_parametric_z_score_calculation`
- `tests/test_audit_and_governance.py::TestAuditStatistics::test_mad_z_score_calculation`
- `tests/test_audit_and_governance.py::TestAuditStatistics::test_hhi_concentration`
- `tests/test_audit_and_governance.py::TestAuditStatistics::test_benford_first_digit_evaluation`
- `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_audit_signal_non_accusatory_enforcement`
- `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_contract_overpricing_rule`
- `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_supplier_concentration_rule`
- `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_ceap_quota_outlier_rule`
- `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_adapter_satisfies_protocol`
- `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_high_severity_routes_to_human_review`
- `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_system1_never_auto_publishes_nominal_accusation`
- `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_official_reply_discount`
- `tests/test_audit_and_governance.py::TestGroundedRAGNarrator::test_narrator_generates_three_epistemic_blocks`
- `tests/test_audit_and_governance.py::TestGroundedRAGNarrator::test_narrator_refuses_empty_provenance`

## 16. Questões Pendentes
Nenhuma questão bloqueante pendente.

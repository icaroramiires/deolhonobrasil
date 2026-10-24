# SPEC-0008 — Detecção de Fracionamento de Despesas (Dispensa de Licitação) e Desvio Estatístico da Lei de Benford em Lotes de Gastos Públicos

## 1. Identificador e Título
- **Identificador:** SPEC-0008
- **Título:** Detecção de Fracionamento de Despesas (Dispensa de Licitação) e Desvio Estatístico da Lei de Benford em Lotes de Gastos Públicos

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0
- **Data:** 2026-10-24

## 3. Problema e Motivação
A fiscalização automatizada de grandes volumes de despesas públicas exige mecanismos estatísticos e temporais capazes de identificar padrões anômalos que possam sugerir elisão de licitação (fracionamento artificiais de despesas para manutenção sob o teto de dispensa) ou manipulação e falsificação numérica de dados contábeis (desvio da Lei de Benford). O motor de auditoria do *De Olho no Brasil* precisa incorporar regras robustas, determinísticas e transparentes para avaliar essas duas dimensões sem emitir juízos acusatórios.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Implementar a regra estatística de conformidade com a Lei de Benford (`evaluate_benford_distribution_rule`) com cálculo de MAD (*Mean Absolute Deviation*) e Qui-Quadrado.
- Implementar a regra de detecção de fracionamento de despesas (`evaluate_split_expense_rule`) com janelas deslizantes temporais por fornecedor e órgão.
- Garantir rastreabilidade integral com hashes SHA-256 (`provenance_hashes`).

### Não-Objetivos
- Emitir vereditos automatizados de crime de corrupção ou fraude comprovada.
- Substituir a análise pericial humana de justificativas de planejamento de compras.

## 5. Atores e Permissões
- **Auditor Automatizado (Laya / Sistema):** Executa as regras de auditoria em lote.
- **Analista de Controle / Cidadão Auditor:** Consulta os sinais gerados, respeitando a governança de triagem interna (`EM_TRIAGEM_INTERNA`).

## 6. Fluxos Principais
1. Ingestão de lote de despesas públicas.
2. Execução da verificação estatística de primeiro dígito (Benford) para lotes com $N \ge 50$.
3. Execução da varredura temporal por janela deslizante (ex: 90 dias) para agrupamento de despesas por fornecedor abaixo do limite de dispensa.
4. Emissão de `AuditSignal` correspondente com hashes de proveniência e métricas calculadas.

## 7. Cenários Alternativos e de Erro
- **Amostra Insuficiente ($N < 50$):** A avaliação de Benford retorna `None` ou sinal de amostra insuficiente, evitando falsos positivos estatísticos.
- **Transações Espaçadas no Tempo:** Despesas abaixo do teto mas distantes temporalmente além da janela deslizante não disparam o alerta de fracionamento.
- **Múltiplos Favorecidos Distintos:** Pagamentos a fornecedores diferentes não são somados indevidamente para cálculo de fracionamento.

## 8. Requisitos Funcionais
- **`FR-018`:** O motor de auditoria deve implementar `evaluate_benford_distribution_rule` (`R-STAT-BENFORD-DEVIATION`), avaliando a conformidade do primeiro dígito de populações de despesas com a Lei de Benford (`evaluate_benford_first_digit`) e emitindo `AuditSignal` com MAD e Qui-Quadrado quando a distribuição for `NAO_CONFORME` (MAD > 0.01500).
- **`FR-019`:** O motor de auditoria deve implementar `evaluate_split_expense_rule` (`R-SPLIT-EXPENSE-THRESHOLD`), agrupando despesas por fornecedor (`supplier_doc_normalized`) e órgão em uma janela deslizante temporal (ex: 90 dias) e emitindo `AuditSignal` quando valores individuais abaixo do teto de dispensa somarem quantia superior ao limite agregado legal.

## 9. Requisitos Não Funcionais
- **`NFR-011`:** Ordenação temporal determinística e processamento em $O(N \log N)$ em memória para cálculo de janelas móveis de fracionamento, sem dependências externas.

## 10. Regras de Negócio e Dados
- **`DATA-010`:** Agregação estrita de proveniência (`provenance_hashes`) contendo a união dos hashes `SHA-256` dos lotes brutos envolvidos no cálculo estatístico ou no grupo fracionado.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-011`:** Vedação irrestrita a termos acusatórios (`assert_non_accusatory_language`) e explicitação no bloco de limitação das hipóteses de conformidade legal (compras para objetos distintos, serviços imprevisíveis e valores tabelados de diárias/passagens).

## 12. Critérios de Aceite
- **`AC-030`:** `evaluate_benford_distribution_rule` detecta desvios estatísticos significativos (MAD > 0.01500) e emite `AuditSignal` válido.
- **`AC-031`:** `evaluate_benford_distribution_rule` retorna `None` para amostras com menos de 50 despesas ou em conformidade.
- **`AC-032`:** `evaluate_split_expense_rule` identifica agrupamentos de despesas por fornecedor e órgão dentro da janela deslizante que superam o teto agregado.
- **`AC-033`:** `evaluate_split_expense_rule` ignora despesas isoladas ou abaixo do limiar de alerta.

## 13. Dependências
- `SPEC-0001` (Core Audit Signals e Arquitetura Base)
- `SPEC-0002` (Normalização de Documentos e Hash SHA-256)
- `SPEC-0003` (Motor de Regras Laya e Camada de Inferência)

## 14. Riscos e Limitações
- Falsos positivos em Benford devido a faixas restritas de valores (ex: lotes estritamente de passagens aéreas tabeladas).
- Justificativas legítimas de entregas parceladas em contratos continuados.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_benford_and_split_expenses.py::TestBenfordAndSplitExpenseRules::test_benford_rule_detects_non_conformant_distribution_and_emits_signal`
- `tests/test_benford_and_split_expenses.py::TestBenfordAndSplitExpenseRules::test_benford_rule_returns_none_for_conformant_or_small_sample`
- `tests/test_benford_and_split_expenses.py::TestBenfordAndSplitExpenseRules::test_split_expense_rule_detects_clustering_within_rolling_window`
- `tests/test_benford_and_split_expenses.py::TestBenfordAndSplitExpenseRules::test_split_expense_rule_ignores_isolated_transactions_or_below_aggregate_threshold`

## 16. Questões Pendentes
- Nenhuma.

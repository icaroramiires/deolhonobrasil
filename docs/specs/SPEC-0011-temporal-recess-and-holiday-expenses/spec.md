# SPEC-0011 — Detecção de Despesas em Fins de Semana, Feriados Nacionais e Recessos Parlamentares (Padrões Temporais Atípicos)

## 1. Identificador e Título
- **ID:** `SPEC-0011`
- **Título:** Detecção de Despesas em Fins de Semana, Feriados Nacionais e Recessos Parlamentares (Padrões Temporais Atípicos)

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0

## 3. Problema e Motivação
Despesas parlamentares (como CEAP/CEAPS) emitidas em períodos de recesso legislativo, fins de semana ou feriados nacionais exigem escrutínio estatístico diferenciado. Embora exista atividade legítima nas bases eleitorais, a concentração de gastos presenciais (hospedagem, combustível, alimentação) em datas de inatividade congressual formal ou a emissão em dias sem expediente administrativo representam desvios estatísticos atípicos que necessitam de sinalização transparente para auditoria cívica.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Automatizar a identificação de despesas presenciais em sábados, domingos e feriados nacionais oficiais.
- Identificar clusters de despesas acima de limiares monetários e quantitativos durante os recessos parlamentares constitucionais.
- Preservar rigorosa separação epistêmica e linguagem não-acusatória, reconhecendo a legitimidade da atuação na base eleitoral.

### Não-Objetivos
- Emitir juízo de valor ou caracterizar crime/irregularidade automática sobre as despesas temporais atípicas.
- Substituir a análise fiscal humana e a manifestação do parlamentar.

## 5. Atores e Permissões
- **Sistema de Auditoria (Automático):** Executa as regras `R-TEMPORAL-WEEKEND-HOLIDAY` e `R-TEMPORAL-PARLIAMENTARY-RECESS`.
- **Auditor Humano / Cidadão:** Visualiza os sinais gerados, respeitando as políticas de RLS e LGPD.

## 6. Fluxos Principais
1. O pipeline de auditoria ingere lotes de despesas normalizadas com hashes `SHA-256`.
2. O motor verifica a data de emissão de cada despesa contra o calendário civil (fins de semana e feriados oficiais móveis/fixos).
3. O motor verifica o agrupamento de despesas nas janelas constitucionais de recesso parlamentar.
4. São gerados objetos `AuditSignal` contendo a proveniência dos dados, métricas estatísticas e classificação adequada.

## 7. Cenários Alternativos e de Erro
- **Despesas remotas ou de divulgação institucional:** Categorias como divulgação da atividade parlamentar ou assinaturas digitais não exigem presença física e são ignoradas pela regra de fins de semana/feriados.
- **Despesas residuais em recesso:** Gastos isolados abaixo do limiar acumulado (R$ 15.000,00 e 3 despesas) durante o recesso são filtrados, evitando falsos positivos excessivos.
- **Feriados móveis:** Cálculo preciso de feriados nacionais móveis (ex.: Carnaval, Páscoa, Corpus Christi) através de algoritmos astronômicos padrão (Meeus/Butcher) em Python puro.

## 8. Requisitos Funcionais
- `FR-024`: O motor de auditoria deve implementar `evaluate_weekend_holiday_expense_rule` (`R-TEMPORAL-WEEKEND-HOLIDAY`), identificando despesas de presença física (combustível, refeições, hospedagem, transporte) emitidas em sábados, domingos e feriados nacionais oficiais (Leis nº 662/1949, 10.607/2002 e 14.759/2023), emitindo `AuditSignal` com proveniência e classificação `STATISTICAL_ANOMALY`.
- `FR-025`: O motor de auditoria deve implementar `evaluate_parliamentary_recess_expense_rule` (`R-TEMPORAL-PARLIAMENTARY-RECESS`), identificando quando um mesmo agente público acumula despesas de cota que superem o limiar de relevância (ex.: R$ 15.000,00 e >= 3 despesas) durante as janelas de recesso parlamentar constitucional (art. 57 da CF/88: 23/dez a 01/fev e 18 a 31/jul), emitindo `AuditSignal` com proveniência de todas as despesas do período.

## 9. Requisitos Não Funcionais
- `NFR-014`: Algoritmo de cálculo de feriados nacionais e janelas temporais executado com complexidade $O(N)$ em memória usando estritamente a biblioteca padrão do Python (`datetime`, `calendar`), sem pacotes externos.

## 10. Regras de Negócio e Dados
- `DATA-013`: Agrupamento de proveniência (`provenance_hashes`) agregando a totalidade dos hashes `SHA-256` das despesas auditadas em fim de semana/feriado ou durante o recesso.

## 11. Requisitos de Segurança e Privacidade
- `SEC-014`: Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que a atividade parlamentar na base eleitoral pode ocorrer legitimamente em fins de semana, feriados e períodos de recesso legislativo.

## 12. Critérios de Aceite
- `AC-042`: `evaluate_weekend_holiday_expense_rule` detecta despesas presenciais em sábados, domingos ou feriados nacionais e emite sinal.
- `AC-043`: `evaluate_weekend_holiday_expense_rule` ignora despesas em dias úteis comuns ou categorias não-presenciais (ex.: divulgação da atividade parlamentar, assinaturas).
- `AC-044`: `evaluate_parliamentary_recess_expense_rule` detecta gastos acumulados acima do recesso constitucional (23/dez a 01/fev e 18 a 31/jul) e emite sinal.
- `AC-045`: `evaluate_parliamentary_recess_expense_rule` ignora despesas fora dos períodos de recesso ou que fiquem abaixo do limiar acumulado.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0008`, `SPEC-0010`

## 14. Riscos e Limitações
- Possibilidade de falsos positivos devido a viagens oficiais autorizadas e atendimento a eleitores em fins de semana ou recessos. Mitigado pela classificação restrita a `STATISTICAL_ANOMALY` e notas explicativas obrigatórias.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_weekend_holiday_expense_rule_detects_weekend_or_holiday`
- `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_weekend_holiday_expense_rule_ignores_weekday_or_remote_category`
- `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_parliamentary_recess_rule_detects_cluster_above_threshold`
- `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_parliamentary_recess_rule_ignores_below_threshold_or_outside_recess`

## 16. Questões Pendentes
- Nenhuma.

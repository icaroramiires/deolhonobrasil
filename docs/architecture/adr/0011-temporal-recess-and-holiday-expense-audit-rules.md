# ADR-0011: Detecção de Despesas em Fins de Semana, Feriados Nacionais e Recessos Parlamentares

- **Status:** Aceito e Em Implementação
- **Data:** 2026-10-24
- **Especificação Relacionada:** [`SPEC-0011-temporal-recess-and-holiday-expenses`](../../specs/SPEC-0011-temporal-recess-and-holiday-expenses/spec.md)
- **Requisitos Atendidos:** `FR-024`, `FR-025`, `NFR-014`, `DATA-013`, `SEC-014`, `AC-042..045`

---

## 1. Contexto

A atividade parlamentar e o uso de verbas indenizatórias de gabinete (CEAP/CEAPS) apresentam sazonalidade e periodicidade vinculadas ao calendário oficial:
1. **Fins de Semana e Feriados Nacionais:** Gastos de consumo presencial imediato (combustível, refeições, alimentação, diárias de hospedagem) emitidos em dias não úteis (sábados, domingos e feriados federais) quando não há sessões deliberativas convocadas no Congresso Nacional.
2. **Recessos Parlamentares Constitucionais:** Períodos regimentais estipulados pelo art. 57 da Constituição Federal (recesso de verão: 23 de dezembro a 1º de fevereiro; recesso de inverno: 18 a 31 de julho), onde a atividade plenária ordinária encontra-se constitucionalmente suspensa, ensejando auditoria sobre picos ou concentrações expressivas de despesas públicas acumuladas.

---

## 2. Decisão Arquitetural

1. **Cálculo de Feriados Nacionais na Biblioteca Padrão (Sem Dependências Externas):**
   - Implementar cálculo de feriados nacionais brasileiros fixos (Leis nº 662/1949, 10.607/2002 e 14.759/2023) e feriados móveis derivados da Páscoa (Algoritmo Meeus/Butcher de Páscoa, Carnaval, Sexta-feira Santa e Corpus Christi) usando exclusivamente tipos nativos (`datetime.date`).
2. **Regra de Despesas em Finais de Semana e Feriados Nacionais (`R-TEMPORAL-WEEKEND-HOLIDAY`):**
   - Filtra despesas de categorias presenciais (`"COMBUSTIVEL"`, `"ALIMENTACAO"`, `"HOSPEDAGEM"`, `"LOCACAO DE VEICULO"`, `"TAXI"`).
   - Verifica se a data de emissão (`issue_date`) recai em sábado (weekday 5), domingo (weekday 6) ou feriado nacional oficial.
   - Emite `AuditSignal` com proveniência `SHA-256` e classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
3. **Regra de Gastos Concentrados em Recesso Parlamentar (`R-TEMPORAL-PARLIAMENTARY-RECESS`):**
   - Avalia despesas do mesmo agente público (`public_agent_id`) emitidas dentro das janelas constitucionais do art. 57 da CF/88 (23/dez a 01/fev e 18 a 31/jul).
   - Para evitar ruído estatístico em gastos habituais residuais, ativa o sinal quando a soma acumulada de despesas no período ultrapassar um limiar configurável (ex.: `Decimal("15000.00")` e ao menos 3 despesas).
   - Emite `AuditSignal` com agregação de proveniência de todas as despesas da janela de recesso.
4. **Governança Epistêmica e Linguagem Não-Acusatória (`SEC-014`):**
   - Destacar expressamente nas limitações que o exercício do mandato parlamentar ocorre de forma ininterrupta, e que compromissos comunitários, agendas políticas municipais, encontros com eleitores e despesas de apoio parlamentar podem ocorrer de forma plenamente legítima em fins de semana, feriados ou durante os recessos legislativos.

---

## 3. Consequências

- **Positivas:** Permite identificar com exatidão analítica temporal anomalias de gasto e consumo atípico sem impor dependências externas pesadas (como pacotes de terceiros de calendário), preservando o footprint zero-dependency do pipeline core.

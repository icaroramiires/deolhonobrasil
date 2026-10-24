# Technical Design Plan — SPEC-0011

## 1. Visão Geral
Este documento detalha o design técnico para as funções `evaluate_weekend_holiday_expense_rule` e `evaluate_parliamentary_recess_expense_rule` em `src/deolhonobrasil/audit/rules.py`.

## 2. Estrutura de Módulos e Funções
- `evaluate_weekend_holiday_expense_rule(expense)`: Valida se a despesa possui categoria presencial e se foi emitida em fim de semana ou feriado nacional oficial.
- `evaluate_parliamentary_recess_expense_rule(agent_id, expenses_in_period)`: Analisa o cluster de despesas de um agente durante as janelas constitucionais de recesso parlamentar.

## 3. Algoritmo de Feriados Nacionais e Recessos
- Feriados fixos: 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 25/12, mais feriados móveis calculados via Meeus/Butcher (Carnaval, Sexta-Feira Santa, Corpus Christi).
- Recessos constitucionais (Art. 57 CF/88):
  - 23 de dezembro a 1 de fevereiro.
  - 18 de julho a 31 de julho.

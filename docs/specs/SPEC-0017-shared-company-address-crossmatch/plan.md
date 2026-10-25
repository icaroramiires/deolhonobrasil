# Technical Design Plan — SPEC-0017

## 1. Visão Geral da Arquitetura
Implementação do módulo de normalização de endereços e da regra de auditoria `evaluate_shared_company_address_rule` dentro do motor Laya / pacote de auditoria de pessoas jurídicas.

## 2. Componentes Principais
- `CuratedCompanyRegistrationRecord`: Modelo Pydantic para ingestão de dados da Receita Federal com validação de CEP e campos de logradouro.
- `compute_normalized_address_key`: Função determinística de normalização e geração de hash SHA-256 (`DATA-019`, `NFR-020`).
- `evaluate_shared_company_address_rule`: Regra determinística (`R-CORP-SHARED-ADDRESS`) que avalia contratos e despesas de órgãos públicos para detectar fornecedores com endereços físicos idênticos.

## 3. Tratamento de Casos Especiais
- Descarte de salas e unidades autônomas distintas em condomínios corporativos.
- Validação de órgãos contratantes distintos para evitar falsos positivos.

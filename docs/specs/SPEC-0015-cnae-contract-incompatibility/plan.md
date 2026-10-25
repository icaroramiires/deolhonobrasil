# Technical Design & Plan — SPEC-0015

## 1. Visão Geral da Arquitetura
O módulo `donb.audit.rules.cnae_incompatibility` implementará:
- `CuratedCompanyRegistrationRecord`: Pydantic model validando CNPJ, hash SHA-256 do payload bruto, `main_cnae_code` ($\text{\textbackslash d}\{7\}$) e `secondary_cnae_codes` (tupla de strings de 7 dígitos).
- `evaluate_cnae_contract_incompatibility_rule`: Função pura de auditoria que verifica se a divisão (2 primeiros dígitos) do objeto do contrato possui interseção com o CNAE principal ou secundários da empresa contratada, respeitando o limite de valor de $R\$ 50.000,00$.

---

## 2. Componentes e Estrutura de Arquivos
- `src/deolhonobrasil/models/company.py` (ou extensão correspondente)
- `src/deolhonobrasil/audit/rules/cnae_incompatibility.py`
- `tests/test_cnae_contract_incompatibility.py`

---

## 3. Plano de Execução Técnica
1. Criar modelos de dados imutáveis com validação regex estrita para CNAE.
2. Implementar o mapeamento setorial e a função de avaliação de regra.
3. Escrever os 4 testes de âncora especificados em `spec.md`.
4. Executar o harness de verificação.

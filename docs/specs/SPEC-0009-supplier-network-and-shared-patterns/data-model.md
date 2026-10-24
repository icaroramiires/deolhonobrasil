# Modelo de Dados — SPEC-0009

## 1. Estrutura de Extração de Raiz
- Entrada: String de identificador (CNPJ ou CPF/máscara).
- Saída: `str` de 8 dígitos (`raiz_cnpj`) ou `None`.

## 2. Sinal de Grupo Econômico / Monopólio
- `AuditSignal`:
  - `rule_id`: `R-SHARED-CNPJ-ROOT` ou `R-PROCUREMENT-MONOPOLISTIC-SUPPLIER`
  - `score`: `float` (0.0 a 1.0)
  - `provenance_hashes`: `List[str]` (Lista consolidada de hashes SHA-256)
  - `metadata`: Dicionário com montante total, filiais envolvidas e percentual de concentração.

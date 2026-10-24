# Plano Técnico (Design) — SPEC-0009

## 1. Visão Geral da Arquitetura
As funções e regras serão implementadas no módulo `src/deolhonobrasil/audit/rules.py`:
- `extract_cnpj_root(cnpj: str) -> Optional[str]`: Valida se a string possui 14 dígitos numéricos (ou formados por dígitos) e extrai os 8 primeiros dígitos. Retorna `None` para CPFs (11 dígitos) ou formatos inválidos / mascarados.
- `evaluate_shared_cnpj_root_rule(...)`: Identifica pagamentos para diferentes estabelecimentos (filiais) com a mesma raiz de CNPJ em um mesmo órgão.
- `evaluate_monopolistic_supplier_category_rule(...)`: Avalia concentração de gastos em um único fornecedor/grupo (>= 80%, mínimo de R$ 100.000,00 e 3 transações).

## 2. Tratamento de Erros e Limitações
- Garantir que CPFs mascarados (`***.XXX.XXX-**`) sejam filtrados sem lançar exceções.
- Garantir a compilação limpa e conformidade com os testes de ancoragem.

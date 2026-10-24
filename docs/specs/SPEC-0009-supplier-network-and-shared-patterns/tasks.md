# Decomposição de Tarefas — SPEC-0009 (Jira: DONB-16)

- [ ] `TASK-0901`: Implementar a função `extract_cnpj_root` com validação de 14 dígitos e rejeição de CPFs e máscaras.
- [ ] `TASK-0902`: Implementar a regra `evaluate_shared_cnpj_root_rule` (`R-SHARED-CNPJ-ROOT`) para agrupamento de filiais por órgão.
- [ ] `TASK-0903`: Implementar a regra `evaluate_monopolistic_supplier_category_rule` (`R-PROCUREMENT-MONOPOLISTIC-SUPPLIER`) com limiares de 80%, R$ 100k e 3 transações.
- [ ] `TASK-0904`: Criar suíte de testes unitários em `tests/test_shared_cnpj_root_and_monopoly.py` validando todos os quatro test anchors.

# SPEC-0009 — Detecção de Vínculo Societário por Radical de CNPJ Compartilhado (Matriz e Filiais) e Concentração Monopolística de Fornecedores

## 1. Identificador e Título
- **ID:** `SPEC-0009`
- **Título:** Detecção de Vínculo Societário por Radical de CNPJ Compartilhado (Matriz e Filiais) e Concentração Monopolística de Fornecedores

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0

## 3. Problema e Motivação
Na análise de execução orçamentária e licitações públicas, fornecedores distintos podem aparentar concorrência nominal quando na verdade pertencem ao mesmo grupo econômico (matriz e filiais com a mesma raiz de 8 dígitos de CNPJ). Além disso, a concentração excessiva de repasses em um único grupo ou fornecedor dentro de um mesmo órgão ou categoria de despesa pode indicar dependência ou exclusividade de mercado que merece escrutínio estatístico. O sistema precisa automatizar a extração de raízes de CNPJ, agrupar transações corporativas e sinalizar concentrações monopolísticas respeitando rigorosamente a separação epistêmica e a proibição de linguagem acusatória.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Implementar extração estrita de raiz de CNPJ (8 primeiros dígitos) com validação de formato de 14 dígitos.
- Rejeitar categoricamente CPFs e strings mascaradas (`***.XXX.XXX-**`) para evitar falsos positivos por homonímia.
- Implementar a regra determinística `evaluate_shared_cnpj_root_rule` (`R-SHARED-CNPJ-ROOT`) para identificar despesas fragmentadas entre filiais do mesmo grupo em um mesmo órgão.
- Implementar a regra determinística `evaluate_monopolistic_supplier_category_rule` (`R-PROCUREMENT-MONOPOLISTIC-SUPPLIER`) para detectar concentração monopolística (>= 80% do total gasto com mínimo de R$ 100.000,00 e 3 transações).
- Consolidar `provenance_hashes` agregrando todos os hashes SHA-256 das transações componentes.

### Não-Objetivos
- Realizar cruzamento automatizado com a base da Receita Federal para descoberta de sócios ocultos (foco exclusivo na raiz do CNPJ).
- Emitir juízo de valor ou caracterizar crime de cartel sem investigação humana e triagem interna.

## 5. Atores e Permissões
- **Auditor / Analista de Controle Social:** Visualiza os sinais de auditoria, metadados e provas documentais.
- **Sistema Automático (Motor de Auditoria `Laya`):** Executa as regras de forma determinística sobre a base de pagamentos/contratos.
- **Leitor Público (`public_reader`):** Acessa apenas dados validados e não restritos por políticas de RLS.

## 6. Fluxos Principais
1. **Ingestão e Normalização:** O sistema recebe lotes de pagamentos/contratos contendo CNPJs e CPFs.
2. **Extração de Raiz (`extract_cnpj_root`):** O motor valida se o identificador é um CNPJ válido de 14 dígitos e extrai os 8 primeiros dígitos. Se for CPF ou inválido, retorna `None`.
3. **Avaliação de Vínculo de Grupo (`evaluate_shared_cnpj_root_rule`):** Agrupa transações por órgão e raiz de CNPJ, verificando se há múltiplos estabelecimentos distintos capturando recursos.
4. **Avaliação de Concentração (`evaluate_monopolistic_supplier_category_rule`):** Calcula a participação percentual de cada grupo/fornecedor por órgão/categoria.
5. **Emissão de Sinal (`AuditSignal`):** Gera o sinal com score, justificativa técnica, proveniência consolidada (`SHA-256`) e classificações epistêmicas.

## 7. Cenários Alternativos e de Erro
- **Fornecedor com CPF mascarado:** O identificador é um CPF ou string mascarada (`***.XXX.XXX-**`). `extract_cnpj_root` retorna `None`, evitando falsos positivos.
- **Filial única sem concorrência:** Órgão contrata apenas um estabelecimento sem outros CNPJs da mesma raiz. A regra de grupo econômico não dispara sinal indevido.
- **Mercado pulverizado:** Nenhuma empresa atinge o limiar de 80% de concentração. A regra monopolística não emite sinal.

## 8. Requisitos Funcionais
- `FR-020`: O motor de auditoria deve implementar a extração de raiz de CNPJ (`extract_cnpj_root`) e a regra determinística `evaluate_shared_cnpj_root_rule` (`R-SHARED-CNPJ-ROOT`), identificando quando despesas ou contratos de um mesmo órgão são distribuídos entre filiais/estabelecimentos que compartilham a mesma raiz societária de 8 dígitos (`raiz_cnpj`), emitindo `AuditSignal` com proveniência e montante consolidado do grupo econômico.
- `FR-021`: O motor de auditoria deve implementar a regra determinística `evaluate_monopolistic_supplier_category_rule` (`R-PROCUREMENT-MONOPOLISTIC-SUPPLIER`), identificando órgãos ou categorias de despesa onde um único grupo empresarial (mesmo radical) captura >= 80% do total gasto (com mínimo de R$ 100.000,00 e ao menos 3 transações).

## 9. Requisitos Não Funcionais
- `NFR-012`: Extração estrita de raiz societária apenas para CNPJ válido de 14 dígitos, retornando `None` para CPFs mascarados para impedir categoricamente falsos positivos por homonímia.

## 10. Regras de Negócio e Dados
- `DATA-011`: Agrupamento de proveniência (`provenance_hashes`) agregando a totalidade dos hashes `SHA-256` das transações de todas as filiais componentes do grupo econômico identificado.

## 11. Requisitos de Segurança e Privacidade
- `SEC-012`: Aplicação obrigatória de `assert_non_accusatory_language`, explicitando nas limitações que empresas do mesmo grupo econômico (matriz e filiais) possuem autorização legal para operar com CNPJs distintos e que a concentração pode decorrer de especialização técnica exclusiva ou ausência de outros prestadores locais credenciados.

## 12. Critérios de Aceite
- `AC-034`: `extract_cnpj_root` extrai corretamente os 8 primeiros dígitos de um CNPJ de 14 dígitos e retorna `None` para CPFs e formatos inválidos.
- `AC-035`: `evaluate_shared_cnpj_root_rule` detecta transações de filiais distintas do mesmo grupo em um órgão e consolida o montante e hashes de proveniência.
- `AC-036`: `evaluate_monopolistic_supplier_category_rule` identifica concentração >= 80% com mínimo de R$ 100.000,00 e 3 transações.
- `AC-037`: Todos os sinais emitidos utilizam linguagem estritamente não-acusatória e cumprem a separação epistêmica.

## 13. Dependências
- `SPEC-0001` (Arquitetura Base e Motor Laya)
- `SPEC-0002` (Normas de LGPD e Anonimização)
- `SPEC-0003` (Rastreabilidade SHA-256)
- `SPEC-0008` (Normalização de Fornecedores)

## 14. Riscos e Limitações
- Filiais de grandes empresas em regiões remotas podem ser os únicos fornecedores viáveis para determinados serviços, gerando alertas que exigem triagem humana cuidadosa.

## 15. Estratégia de Testes e Test Anchors
Os testes automatizados devem ser implementados no arquivo:
- `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_extract_cnpj_root_validates_14_digits_and_rejects_cpf`
- `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_shared_cnpj_root_rule_detects_multiple_branches_for_same_organ`
- `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_shared_cnpj_root_rule_ignores_single_branch_or_unrelated_cnpjs`
- `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_monopolistic_supplier_category_rule_detects_dominance`

## 16. Questões Pendentes
- Nenhuma.

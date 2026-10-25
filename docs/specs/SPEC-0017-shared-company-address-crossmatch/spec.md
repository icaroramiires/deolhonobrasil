# SPEC-0017 — Indícios de Conluio e Empresas de Fachada: Identificação de Fornecedores com Mesmo Endereço Físico Cadastral (Logradouro, Número e CEP na RFB) Contratados pelo Mesmo Órgão

## 1. Identificador e Título
- **ID:** `SPEC-0017`
- **Título:** Indícios de Conluio e Empresas de Fachada: Identificação de Fornecedores com Mesmo Endereço Físico Cadastral (Logradouro, Número e CEP na RFB) Contratados pelo Mesmo Órgão
- **Área:** Motor de Auditoria e Ingestão de Dados (De Olho no Brasil)

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`
- **Data de Atualização:** 2026-10-25

## 3. Problema e Motivação
A participação e contratação concorrente de pessoas jurídicas distintas que compartilham exatamente o mesmo endereço físico perante a Receita Federal é apontada pelo TCU — Acórdãos 1.793/2011, 2.909/2012 e 1.250/2016-Plenário — e pelo art. 14, § 1º da Lei 14.133/2021 como forte tipologia de fraude, conluio ou empresas fictícias/de fachada, caracterizando simulação de concorrência em licitações públicas ou direcionamento de contratações.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Modelar de forma imutável e estruturada os endereços cadastrais de fornecedores oriundos da Receita Federal.
- Implementar regra de auditoria determinística (`R-CORP-SHARED-ADDRESS`) para detectar fornecedores distintos com o mesmo endereço físico contratados pelo mesmo órgão público.
- Emitir sinais de auditoria com rastreabilidade SHA-256 e proveniência estrita.

### Não-Objetivos
- Emitir penalidades automáticas ou caracterizar dolo sem vistoria in loco preliminar.
- Analisar endereços internacionais ou sem cadastro formal na RFB.

## 5. Atores e Permissões
- **Auditor Automatizado (Motor Laya):** Executa rotinas de cruzamento de endereços.
- **Analista / Auditor Humano:** Revisa achados em `EM_TRIAGEM_INTERNA`.
- **Leitor Público (`public_reader`):** Acessa apenas dados validados e anonimizados.

## 6. Fluxos Principais
1. **Ingestão:** Carregamento de registros cadastrais de pessoas jurídicas (`CuratedCompanyRegistrationRecord`).
2. **Normalização e Assinatura:** Geração de chave de endereço físico normalizada (`compute_normalized_address_key`).
3. **Cruzamento:** Execução de `evaluate_shared_company_address_rule` cruzando contratos (`CuratedPublicContract`) ou despesas (`CuratedPublicExpense`).
4. **Emissão de Sinal:** Criação de `AuditSignal` com proveniência múltipla.

## 7. Cenários Alternativos e de Erro
- **Edifícios comerciais com salas autônomas distintas, coworkings ou incubadoras:** Tratados com descarte do sinal quando identificadas unidades/salas autônomas distintas declaradas.
- **Empresas do mesmo grupo:** Verificação de vínculos societários pré-existentes.
- **Órgãos distintos sem relação:** Descarte de sinais onde os órgãos contratantes são diferentes.

## 8. Requisitos Funcionais
- **`FR-036`:** Ingestão, validação e modelagem imutável de endereço cadastral de pessoas jurídicas (`CuratedCompanyRegistrationRecord` / `OfficialSource.RECEITA_FEDERAL_CNPJ`) incluindo CEP normalizado de 8 dígitos (`postal_code`), logradouro, número, complemento e chave de endereço físico normalizada (`compute_normalized_address_key`).
- **`FR-037`:** O motor de auditoria deve implementar a regra determinística `evaluate_shared_company_address_rule` (`R-CORP-SHARED-ADDRESS`), identificando quando dois ou mais fornecedores com CNPJs distintos que compartilham o mesmo endereço físico exato (mesmo CEP, logradouro e número cadastrais) são contratados (`CuratedPublicContract`) ou favorecidos por despesas (`CuratedPublicExpense`) pelo mesmo órgão público, emitindo `AuditSignal` com proveniência múltipla `SHA-256` e classificação `CROSS_SOURCE_DIVERGENCE`.

## 9. Requisitos Não Funcionais
- **`NFR-020`:** Normalização determinística de endereços em memória em $O(N)$ eliminando pontuações, normalizando abreviações ("RUA", "AV", "AVENIDA", "RODOVIA") e ignorando diferenças de caixa alta/baixa.

## 10. Regras de Negócio e Dados
- **`DATA-019`:** Chave de assinatura física de endereço composta por CEP de 8 dígitos, logradouro limpo e número, com proveniência estrita `OfficialSource.RECEITA_FEDERAL_CNPJ`.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-020`:** Vedação absoluta a termos acusatórios (`assert_non_accusatory_language`), explicitando no bloco de limitações que centros empresariais, incubadoras de base tecnológica, condomínios corporativos e espaços de coworking podem abrigar licitamente múltiplas empresas no mesmo endereço, demandando vistoria in loco preliminar formal antes de qualquer imputação sancionatória.

## 12. Critérios de Aceite
- **`AC-066`:** Modelo valida campos de endereço cadastral, normaliza CEP para 8 dígitos numéricos e gera assinatura única com SHA-256.
- **`AC-067`:** `evaluate_shared_company_address_rule` detecta quando múltiplos fornecedores distintos compartilham o mesmo endereço e são contratados pelo mesmo órgão, emitindo sinal com proveniência múltipla.
- **`AC-068`:** `evaluate_shared_company_address_rule` descarta sinal caso os fornecedores estejam sediados em endereços diferentes ou em salas/unidades autônomas declaradas em condomínio corporativo.
- **`AC-069`:** `evaluate_shared_company_address_rule` descarta sinal se os fornecedores prestarem serviços a órgãos contratantes distintos.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0014`, `SPEC-0016`

## 14. Riscos e Limitações
- Falsos positivos decorrentes de grandes edifícios comerciais ou incubadoras. Mitigado por exigência de vistoria in loco e análise de salas autônomas.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_company_address_model_validation_and_normalization`
- `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_detects_multiple_suppliers_at_same_address`
- `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_ignores_different_address_or_autonomous_units`
- `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_ignores_different_organs`

## 16. Questões Pendentes
- Nenhuma.

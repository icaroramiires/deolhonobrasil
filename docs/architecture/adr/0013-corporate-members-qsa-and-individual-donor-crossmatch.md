# ADR 0013 — Cruzamento com Quadro de Sócios e Administradores (QSA/Receita Federal): Sócios Comuns em Contratações e Doações Eleitorais de Pessoas Físicas (TSE)

## Status
Aprovado

## Data
2026-10-24

## Contexto
O ecossistema de compras públicas brasileiro é regulado por normas estritas de integridade concorrencial (Lei nº 14.133/2021, art. 14, IV, que veda a participação de empresas com sócios administradores comuns na mesma licitação) e de financiamento eleitoral (Lei nº 13.165/2015, que proibiu terminantemente doações eleitorais de pessoas jurídicas).

Como pessoas jurídicas não podem doar a campanhas políticas, as doações declaradas são efetuadas exclusivamente por **Pessoas Físicas (PF)**. Na prática investigativa e de controle externo (TCU, CGU e Tribunais de Contas), o cruzamento essencial para detectar relações entre fornecedores de órgãos públicos e campanhas de mandatários contratantes opera em dois saltos:
1. **Fornecedor Contratado (CNPJ)** $\rightarrow$ **Quadro de Sócios e Administradores (QSA/RFB)** $\rightarrow$ **Sócio Pessoa Física (CPF Mascarado / Nome)**;
2. **Sócio Pessoa Física** $\rightarrow$ **Prestação de Contas Eleitorais (TSE)** $\rightarrow$ **Mandatário Contratante / Autor da Despesa**.

Além disso, em dispensas e licitações no mesmo órgão gestor, empresas formalmente distintas que compartilham sócios administradores configuram potencial quebra de competitividade (`R-CROSS-QSA-SHARED-PARTNER`).

O desafio arquitetural e ético consiste em:
- Ingerir dados abertos da Receita Federal (QSA) com chave natural `(cnpj_basico, identificador_socio, nome_socio)`;
- Proteger dados pessoais de sócios segundo a LGPD (preservando o mascaramento `***.XXX.XXX-**` já praticado pela Receita Federal nos dados abertos);
- Prevenir categoricamente falsos positivos por homonímia pura de CPF mascarado em nomes comuns;
- Assegurar linguagem não-acusatória (`assert_non_accusatory_language`), mantendo a classificação epistêmica `CROSS_SOURCE_DIVERGENCE`.

## Decisão
1. **Nova Fonte Oficial e Modelo Imutável:**
   - Adicionar `RECEITA_FEDERAL_CNPJ = "RECEITA_FEDERAL_CNPJ"` ao enum `OfficialSource`.
   - Implementar a dataclass imutável (`frozen=True`, `slots=True`) `CuratedCorporateMemberRecord` em `src/deolhonobrasil/pipeline/models.py`, contendo:
     - `corporate_root_cnpj`: radical de 8 dígitos da empresa (`cnpj_basico`);
     - `full_cnpj_normalized`: CNPJ de 14 dígitos normalizado (se fornecido) ou derivado;
     - `member_name_raw`: nome do sócio sanitizado via `sanitize_untrusted_public_text`;
     - `member_doc_masked`: documento do sócio com máscara LGPD `***.XXX.XXX-**`;
     - `qualification_code`: código de qualificação na RFB (ex.: sócio-administrador, sócio ostensivo);
     - `entry_date`: data de entrada na sociedade (quando disponível);
     - `provenance`: `ProvenanceMetadata` com `OfficialSource.RECEITA_FEDERAL_CNPJ`.
2. **Regras Determinísticas de Auditoria:**
   - `evaluate_qsa_shared_partner_rule` (`R-CROSS-QSA-SHARED-PARTNER`): avalia se fornecedores distintos contratados pelo mesmo órgão público possuem sócios administradores em comum identificados por chave composta `(member_doc_masked, member_name_raw)` com qualificação de administração, emitindo `AuditSignal` com união dos hashes `SHA-256`.
   - `evaluate_qsa_individual_donor_rule` (`R-CROSS-QSA-DONOR-SUPPLIER`): avalia se sócio administrador de empresa contratada realizou doação de pessoa física declarada ao TSE em benefício do mandatário da despesa (`public_agent_id`), vinculando a tripla proveniência `SHA-256` (QSA + Contrato/Despesa + Doação TSE).
3. **Guardas Epistêmicas e de Segurança:**
   - Ambas as regras emitem `EpistemicClassification.CROSS_SOURCE_DIVERGENCE`.
   - O bloco de limitações (`scope_limitation_summary`) explicita expressamente que a participação societária em múltiplos empreendimentos e a realização de doações de pessoa física até o teto legal de 10% dos rendimentos brutos são direitos legítimos previstos em lei, não presumindo má-fé ou irregularidade.
   - Nomes com homonímia que não possuam documento mascarado compatível são descartados.

## Consequências
### Positivas
- Fecha a lacuna clássica de fiscalização cívica pós-2015 decorrente do fim das doações eleitorais por PJ.
- Rastreabilidade tripla auditável (`bundle_sha256` encadeando RFB + Órgão Gestor + TSE).
- 100% aderente aos padrões de privacidade LGPD e governança editorial do De Olho no Brasil.

### Negativas / Mitigações
- A base de dados abertos de QSA da RFB é volumosa; na camada lakehouse os registros devem ser indexados por radical de CNPJ e documento do sócio em tabelas SQLite com índices dedicados.

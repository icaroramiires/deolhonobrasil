# ADR-0007: Cruzamento Multicritério CEIS/CNEP, Divergência entre Fontes e Prevenção de Homonímia LGPD

- **Status:** Aceito e Implementado
- **Data:** 2026-10-23
- **Especificação Relacionada:** [`SPEC-0007-cross-source-sanctions-and-divergence`](../../specs/SPEC-0007-cross-source-sanctions-and-divergence/spec.md)
- **Requisitos Atendidos:** `FR-016`, `FR-017`, `NFR-010`, `DATA-009`, `SEC-010`, `AC-026..029`

---

## 1. Contexto

A fiscalização cívica de gastos públicos exige cruzar contratos (`PNCP_CONTRATOS`) e despesas (`CAMARA_CEAP`, `SENADO_CEAPS`) com o Cadastro Nacional de Empresas Inidôneas e Suspensas / Cadastro Nacional de Empresas Punidas (`CGU_CEIS_CNEP`), bem como verificar divergências na execução de emendas parlamentares (`CGU_EMENDAS`). Contudo, um cruzamento ingênuo pode gerar falsos positivos graves por dois motivos:
1. **Homonímia em CPFs mascarados (`***.XXX.XXX-**`):** Como apenas 6 dígitos centrais são preservados por exigência da LGPD (`SEC-001`), dois cidadãos distintos podem compartilhar a mesma máscara `***.456.789-**`.
2. **Escopo jurídico e vigência temporal da sanção:** Uma sanção no CEIS/CNEP possui intervalo de vigência (`start_date` a `end_date`), pode ter abrangência restrita apenas ao órgão sancionador (ex.: art. 87, III da Lei 8.666/93 / art. 156, III da Lei 14.133/2021) ou estar suspensa por decisão judicial liminar.

---

## 2. Decisão Arquitetural

1. **Entidade Imutável `CuratedSanctionRecord` (`DATA-009`):**
   - Persistida na tabela `curated_sanctions` do `CivicLakehouseStorage`, exigindo `ProvenanceMetadata` com `OfficialSource.CGU_CEIS_CNEP`.
2. **Bloqueio de Cruzamento Automático por CPF Mascarado (`NFR-010`):**
   - A regra determinística `evaluate_ceis_cnep_sanctioned_supplier_rule` (`R-CROSS-CEIS-SANCTIONED-SUPPLIER`) **só executa cruzamento automático sobre CNPJs completos validados de 14 dígitos** (`supplier_doc_type == "CNPJ"`). Registros de pessoas físicas com CPF mascarado são ignorados pelo cruzamento automatizado para eliminar o risco de falso positivo por colisão de máscara.
3. **Proveniência Composta e Taxonomia `CROSS_SOURCE_DIVERGENCE` (`FR-017`, `SEC-010`):**
   - Todo sinal emitido por `R-CROSS-CEIS-SANCTIONED-SUPPLIER` ou `R-CROSS-AMENDMENT-EXECUTION-GAP` recebe `EpistemicClassification.CROSS_SOURCE_DIVERGENCE` (`DIVERGENCIA_ENTRE_REGISTROS`), concatena os `raw_batch_sha256` de ambas as fontes primárias em `provenance_hashes` e exige `requires_human_review = True`.

---

## 3. Consequências

- **Positivas:** Elimina estruturalmente falsos positivos por colisão de CPF mascarado, comprova criptograficamente ambas as pontas do cruzamento (`SHA-256` duplo) e preserva rigorosamente a separação epistêmica.

# ADR 0018 — Burla à Sanção Administrativa e Impedimento de Licitar: Identificação de Sócios e Administradores (QSA) de Fornecedores Contratados com Sanção Vigente no CEIS/CNEP

## Status
Aprovado

## Data
2026-10-26

## Contexto
Na contratação pública e na aplicação do regime sancionatório da Administração Pública brasileira, uma das manobras mais lesivas à integridade concorrencial consiste na burla a sanções de impedimento de licitar e declaração de inidoneidade (previstas na Lei nº 8.666/1993, na Lei nº 12.846/2013 e nos arts. 14, § 1º, II e 160 da Lei nº 14.133/2021). Nesses cenários, sócios-controladores ou administradores de pessoas jurídicas sancionadas constituem novas pessoas jurídicas ou utilizam empresas já existentes de seu patrimônio para participar de certames e celebrar contratos administrativos com o Estado.

A jurisprudência paradigmática do Tribunal de Contas da União (TCU) — notadamente os Acórdãos nº 2.218/2012, nº 1.028/2014, nº 1.986/2016 e nº 1.637/2021-Plenário — pacificou o entendimento de que a extensão dos efeitos da sanção a empresas coligadas ou com sócios comuns é juridicamente cabível por meio da teoria da desconsideração da personalidade jurídica (*disregard doctrine*), desde que comprovada a identidade de sócios com poderes de gestão, identidade de objeto ou simulação.

Para o sistema *De Olho no Brasil*, a automação dessa detecção impõe quatro desafios críticos:
1. **Desambiguação e Salvaguarda Anti-Homonímia:** O Quadro de Sócios e Administradores (QSA/RFB) e as certidões de sanção do CEIS/CNEP (CGU) apresentam CPFs de pessoas físicas em formato mascarado por força da LGPD (`***.XXX.XXX-**`). Uma correspondência baseada unicamente no CPF mascarado acarretaria falsos positivos severos por colisões numéricas. Exige-se, portanto, correspondência estrita e cumulativa entre a máscara de CPF e o nome sanitizado e normalizado da pessoa física, ou correspondência exata de 14 dígitos quando o sócio sancionado for pessoa jurídica;
2. **Janela Temporal de Vigência Sancionatória:** O impedimento ou inidoneidade possui termo inicial (`start_date`) e termo final (`end_date`) delimitados administrativamente. O cruzamento deve confrontar a data do instrumento contratual (`signature_date`) ou da emissão da despesa pública (`issue_date`) contra a vigência temporal da sanção. Sanções já extintas no momento da contratação não configuram contemporaneidade impeditiva;
3. **Encadeamento Criptográfico de Tripla Proveniência:** O achado não decorre de uma fonte isolada, mas da triangulação de três repositórios independentes: o cadastro de sanções da CGU (`OfficialSource.CGU_CEIS_CNEP`), o quadro societário da Receita Federal (`OfficialSource.RECEITA_FEDERAL_CNPJ`) e o instrumento de contratação pública ou despesa (`OfficialSource.PNCP`, `CAMARA_CEAP` ou `SENADO_CEAPS`). O `AuditSignal` deve carregar os três hashes `SHA-256` correspondentes;
4. **Governança Epistêmica e Linguagem Não-Acusatória:** A presença de sócio com sanção ativa no quadro de uma fornecedora contratada constitui indício fático relevante, mas não consubstancia irregularidade automática imputável ao fornecedor ou ao gestor. Sob o devido processo legal (art. 160 da Lei nº 14.133/2021), a desconsideração da personalidade jurídica exige contraditório, apuração de poderes de gerência (excluindo-se cotistas minoritários sem gestão) e verificação de eventuais decisões judiciais liminares que suspendam os efeitos do CEIS/CNEP. O achado é classificado como `CROSS_SOURCE_DIVERGENCE` e submetido obrigatoriamente a `EM_TRIAGEM_INTERNA`.

## Decisão
1. **Regra Determinística de Auditoria (`R-CROSS-SANCTIONED-PARTNER`):**
   - Implementar `evaluate_sanctioned_partner_supplier_rule` em `src/deolhonobrasil/audit/rules.py`:
     - Parâmetros: `corporate_members: Sequence[CuratedCorporateMemberRecord]`, `sanctions: Sequence[CuratedSanctionRecord]`, `contracts: Sequence[CuratedPublicContract] = ()`, `expenses: Sequence[CuratedPublicExpense] = ()`;
     - Indexa sanções ativas por documento (CNPJ de 14 dígitos ou tupla `(cpf_mascarado, nome_normalizado)`);
     - Mapeia empresas contratadas (via contratos com `current_amount > 0` ou despesas com `net_amount > 0`) aos seus respectivos sócios e administradores no QSA;
     - Para cada sócio vinculado a fornecedor contratado, verifica se há sanção cujo período (`start_date` a `end_date`) abranger a data da contratação ou da despesa;
     - Em caso de correspondência positiva contemporânea, emite `AuditSignal` com tripla proveniência;
     - Gravidade calibrada: `severity = 0.85`, com `requires_human_review = True`.

2. **Governança Epistêmica:**
   - Classificação: `EpistemicClassification.CROSS_SOURCE_DIVERGENCE`;
   - Aplicação de `assert_non_accusatory_language`: proibição de termos acusatórios e inclusão de limitação epistêmica detalhada nos termos do Art. 14, § 1º, II e Art. 160 da Lei nº 14.133/2021.

## Consequências
### Positivas
- Permite identificar preventivamente manobras societárias de burla ao regime de inidoneidade e impedimento de licitar.
- Garante total conformidade com a jurisprudência do TCU e com a Lei nº 14.133/2021.
- Execução determinística em memória em $O(N + M)$ sem dependência de serviços externos.

### Negativas / Mitigações
- Sócios minoritários sem poderes gerenciais podem gerar alertas caso a base do QSA não especifique claramente a ausência de poderes administrativos. A mitigação consiste em explicitar tal ressalva nos metadados do sinal e manter o dossiê em triagem interna até verificação humana.

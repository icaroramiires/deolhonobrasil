# ADR 0017 — Indícios de Conluio e Empresas de Fachada: Identificação de Fornecedores com Mesmo Endereço Físico Cadastral Contratados pelo Mesmo Órgão

## Status
Aprovado

## Data
2026-10-25

## Contexto
Na fiscalização de licitações e contratações públicas brasileiras, um dos vetores de fraude e corrupção mais recorrentes consiste na simulação de concorrência e no conluio entre licitantes (cartel ou *bid rigging*). A jurisprudência consolidada do Tribunal de Contas da União (TCU) — expressa em precedentes paradigmáticos como os Acórdãos nº 1.793/2011, nº 2.909/2012 e nº 1.250/2016-Plenário — e as disposições do art. 14, § 1º e art. 9º da Lei nº 14.133/2021 estabelecem que a participação em certames ou o fornecimento concomitante por pessoas jurídicas distintas que compartilham o mesmo endereço físico perante a Receita Federal do Brasil (RFB) configura indício veemente de conluio, empresas de fachada ou quebra de isonomia.

Para o sistema *De Olho no Brasil*, o desafio de detecção e governança impõe:
1. **Normalização Espacial e Cadastral:** O endereço de empresas nos registros públicos da Receita Federal apresenta variações de formatação (ex.: CEP com ou sem hífen, "R.", "RUA", "AV.", "AVENIDA", "S/N", "SN", complementos como salas e andares). É imperativo normalizar deterministamente o CEP (8 dígitos numéricos estritos) e a tupla (logradouro sanitizado, número predial) em $O(1)$;
2. **Distinção de Edifícios Comerciais e Coworkings:** Centros empresariais de grande porte, condomínios corporativos, parques tecnológicos e espaços de *coworking* podem abrigar licitamente centenas de pessoas jurídicas distintas no mesmo número de logradouro. O algoritmo deve ponderar o campo de complemento (ex.: "Sala 101" vs "Sala 902") para não emitir falsos alertas grosseiros quando as unidades autônomas forem inequivocamente distintas;
3. **Segregação Estrita por Órgão Contratante:** O indício de conluio ou simulação de competitividade relevante para compras públicas ocorre quando as empresas que dividem a mesma sede física participam de contratações ou recebem pagamentos do **mesmo órgão licitante** (`organ_code` / `organ_cnpj`). Empresas no mesmo endereço prestando serviços para órgãos públicos completamente independentes (ex.: uma para a Prefeitura de Manaus e outra para o Ministério da Defesa em Brasília) não caracterizam conluio direto no certame;
4. **Governança Epistêmica e Linguagem Não-Acusatória:** A convergência de endereço cadastral não comprova fraude ou conluio judicialmente. Pode decorrer de alteração de sede recente não atualizada na Junta Comercial ou erro material de preenchimento. O achado deve ser classificado como `CROSS_SOURCE_DIVERGENCE` e submetido à revisão humana interna (`EM_TRIAGEM_INTERNA`).

## Decisão
1. **Enriquecimento Cadastral em `CuratedCompanyRegistrationRecord`:**
   - Adicionar atributos opcionais com valores-padrão não-quebrantes em `src/deolhonobrasil/pipeline/models.py`:
     - `postal_code: str = "00000000"` (8 dígitos numéricos);
     - `street_address: str = "N/A"`;
     - `address_number: str = "S/N"`;
     - `address_complement: str | None = None`;
     - `district: str = "CENTRO"`;
     - `city: str = "BRASILIA"`;
     - `state_uf: str = "DF"`;
   - Implementar método auxiliar puro `compute_normalized_address_key(postal_code, street_address, address_number, complement)` gerando uma chave canônica determinística para cruzamento;
   - Atualizar `create_validated()` para aceitar parâmetros de endereço de forma retrocompatível.

2. **Regra Determinística de Auditoria (`R-CORP-SHARED-ADDRESS`):**
   - Implementar `evaluate_shared_company_address_rule` em `src/deolhonobrasil/audit/rules.py`:
     - Parâmetros: `companies: Sequence[CuratedCompanyRegistrationRecord]`, `contracts: Sequence[CuratedPublicContract] = ()`, `expenses: Sequence[CuratedPublicExpense] = ()`;
     - Agrupa contratações e pagamentos por órgão contratante;
     - Para cada órgão, cruza os fornecedores contratados que possuem registros cadastrais disponíveis;
     - Se dois ou mais fornecedores com CNPJs distintos (e raízes societárias distintas, ou filiais não consolidadas) compartilharem a mesma chave canônica de endereço físico, e não houver distinção inequívoca de sala/unidade autônoma independente, emite sinal de auditoria;
     - Montante auditado: soma dos contratos/despesas das empresas colidentes perante o órgão;
     - Proveniência: união de hashes `SHA-256` das empresas envolvidas e dos instrumentos contratuais/despesas.

3. **Governança Epistêmica:**
   - Classificação: `EpistemicClassification.CROSS_SOURCE_DIVERGENCE`;
   - `requires_human_review = True`;
   - Aplicação estrita de `assert_non_accusatory_language`, detalhando expressamente nas limitações que condomínios comerciais e espaços compartilhados de trabalho abrigam empresas regulares e que apenas vistoria in loco e fiscalização prévia podem determinar a realidade física dos estabelecimentos.

## Consequências
### Positivas
- Provê cobertura direta a uma das mais graves e frequentes tipologias de fraude e cartel em licitações apontadas pelo TCU (empresas no mesmo endereço físico competindo entre si ou revezando contratações).
- Retrocompatibilidade absoluta mantida com o modelo existente de `CuratedCompanyRegistrationRecord` através de valores default seguros.
- Execução determinística em memória em $O(N)$ sem dependência de serviços externos de geolocalização.

### Negativas / Mitigações
- Endereços com números cadastrais genéricos ("S/N", "KM 0", "ZONA RURAL") podem gerar falsas colisões se não filtrados. A normalização exige CEP válido e descarta endereços com logradouro em branco ou puramente genérico.

# Visão do Produto — De Olho no Brasil

## 0. Decisão de nome

O nome de trabalho **Verba Clara** foi avaliado em 26 de outubro de 2026 e **não foi adotado**. A página [https://verbaclara.pro/](https://verbaclara.pro/) apresentava, nessa data, o serviço VerbaClara de auditoria de verbas públicas, associado a FISCOIA INOVA SIMPLES (I.S.), CNPJ 67.973.713/0001-02, em Juazeiro do Norte/CE. A busca interativa de marcas no INPI não foi concluída nesta execução, portanto não há conclusão sobre registro marcário. O nome deste repositório permanece **De Olho no Brasil**. A decisão está em [ADR-0022](../architecture/adr/0022-retain-de-olho-no-brasil-name.md).

## 1. Propósito Central
O **De Olho no Brasil** é uma infraestrutura cívica aberta, auditável e colaborativa de fiscalização assistida por inteligência artificial voltada à análise de gastos públicos brasileiros.

A plataforma existe para reduzir a assimetria de informação entre portais governamentais fragmentados e a sociedade civil (cidadãos, jornalistas investigativos, pesquisadores e órgãos de controle), transformando dados brutos oficiais em evidências compreensíveis, matematicamente reconciliadas e juridicamente responsáveis.

## 2. Os Três Diferenciais Estruturais

1. **Rastreabilidade Fim a Fim (`SHA-256`):**
   Cada valor monetário, indicador estatístico ou síntese textual pode ser conferido diretamente na fonte pública primária por meio de sua URL oficial e do hash criptográfico `SHA-256` do lote bruto coletado (`ProvenanceMetadata`).
2. **Confiabilidade e Separação Epistêmica em 3 Camadas:**
   A plataforma jamais apresenta resultados de algoritmos ou de IA como prova de fraude ou culpa. Todo dossiê separa visual e estruturalmente:
   - `[DADO OFICIAL]` — Fato documental extraído da fonte primária e conciliado centavo a centavo.
   - `[INFERÊNCIA ESTATÍSTICA]` — Desvio matemático calculado por regra determinística (`Z-Score`, `MAD Z-Score`, `Índice HHI`, `Lei de Benford`).
   - `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]` — Explicação explícita do que os dados não provam sozinhos, destacando hipóteses operacionais legítimas e exigindo contraditório.
3. **Acessibilidade Cívica e Direito de Resposta Paritário:**
   Qualquer cidadão compreende o gasto, a inconsistência apontada e o que ainda precisa ser esclarecido, enquanto órgãos públicos e fornecedores dispõem de protocolo formal de Direito de Resposta exibido lado a lado com igual destaque visual (`equal_visual_prominence = True`).

## 3. Princípios Inegociáveis de Governança
- **Proibição de Acusação Automática:** Termos como `"fraude comprovada"`, `"corrupção"`, `"roubo"`, `"criminoso"` ou `"culpado"` são bloqueados mecanicamente no código (`assert_non_accusatory_language`).
- **Privacidade por Padrão (LGPD):** CPFs de pessoas físicas comuns são mascarados (`***.XXX.XXX-**`) na camada de ingestão antes de qualquer persistência na camada curada.
- **Revisão Humana Obrigatória para Sinais Sensíveis:** Nenhum dossiê nominal em triagem (`EM_TRIAGEM_INTERNA`) é visível ao leitor público (`PUBLIC_READER`) sem aprovação humana explícita (`reviewer_id IS NOT NULL`).

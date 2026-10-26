# SPEC-0022 — Cobertura pública observada e perguntas determinísticas

## 1. Identificador e Título
- **ID:** `SPEC-0022`
- **Título:** Cobertura pública observada e perguntas determinísticas sobre o lakehouse local

## 2. Status e Versão
- **Status:** `Verificado` na suíte local de 26 de outubro de 2026, 19:09 America/Sao_Paulo (`135/135` testes, harness checkpoint 4, 3 tentativas, `pass_at_1` 1.0 e `pass_hat_k` 1.0)
- **Versão:** `1.0.0`

## 3. Problema e Motivação
O cidadão precisa saber o que este ambiente realmente analisou, sem confundir a amostra visual do wireframe nem o carimbo declarado do catálogo com uma coleta nacional. Perguntas em linguagem simples devem citar somente linhas persistidas e declarar inconclusão quando faltarem dados.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Publicar totais, períodos e fontes calculados das tabelas locais.
- Responder um conjunto fechado de perguntas sem modelo de linguagem.
- Impedir que triagem interna, linguagem vedada ou instruções embutidas na pergunta alterem o resultado.

### Não-Objetivos
- Representar o orçamento da União, dos estados ou dos municípios.
- Extrair PDF, executar OCR ou chamar APIs oficiais nesta especificação.
- Publicar suspeita nominal produzida por modelo.
- Sincronizar Jira ou Confluence.

## 5. Atores e Permissões
- `public_reader`: lê a cobertura e envia perguntas. Não recebe dossiês em `EM_TRIAGEM_INTERNA`.
- `reviewer_admin`: não ganha rota nova neste incremento.

## 6. Fluxos Principais
1. O cliente chama `GET /api/v1/public-coverage`.
2. O serviço soma centavos por fonte e confronta a soma com o total da tabela.
3. O cliente envia `POST /api/v1/questions` com `{"question": "..."}`.
4. O serviço sanitiza o texto, recusa linguagem vedada e executa apenas a consulta correspondente.
5. A página inicial rotula a série do wireframe como amostra e preenche o bloco de cobertura com a resposta da API quando o documento é servido pelo aplicativo.

## 7. Cenários Alternativos e de Erro
- Lakehouse vazio: totais zerados e limitação explícita de que zero não é ausência de gasto público.
- Categoria ou ano sem linha: conclusão `ANALISE_INCONCLUSIVA` e valor monetário `null`.
- Mais de uma categoria reconhecida, ou nenhuma: a resposta pede precisão e lista categorias locais, no máximo oito.
- Pergunta com termo vedado: HTTP 422, sem repetir o termo.
- Pedido de CPF completo ou endereço residencial: recusa sem revelar dado.
- Falha de rede no navegador: o bloco de cobertura informa que não pôde ser carregado e reafirma que os cartões são amostra.

## 8. Requisitos Funcionais
- **`FR-049`**: `GET /api/v1/public-coverage` devolve despesas, contratos, emendas e sanções em ledgers separados, com contagem, centavos, período observado, fontes observadas e limitações. `represents_national_spending` e `ledgers_are_additive` são `false`.
- **`FR-050`**: `POST /api/v1/questions` responde gasto por categoria e ano, diferença aritmética entre dois anos, documento identificado, motivo de regra já publicada ou lacunas públicas de dados. Sem evidência suficiente, a conclusão é `ANALISE_INCONCLUSIVA`.

## 9. Requisitos Não Funcionais
- **`NFR-025`**: o cálculo monetário usa inteiros de centavos e `Decimal` apenas para formatar a string BRL. Nenhum modelo de linguagem é chamado. `uses_language_model` é `false` e `model_id` é `null`.

## 10. Regras de Negócio e Dados
- **`DATA-024`**: a soma dos centavos por fonte de cada ledger fecha com o `SUM` da tabela. Quarentena não entra no total monetário. Despesas, contratos, emendas e sanções não são combinados num total único.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-025`**: a pergunta passa por `assert_non_accusatory_language` e `sanitize_untrusted_text`. A resposta pública não inclui título nem identificador de dossiê em `EM_TRIAGEM_INTERNA`. CPF completo e endereço residencial não são atendidos.

## 12. Critérios de Aceite
- **`AC-086`**: lakehouse vazio devolve zeros, período nulo e a limitação de ausência de linha local.
- **`AC-087`**: três despesas de duas fontes reconciliam 2950 centavos, sem campo de total combinado.
- **`AC-088`**: a categoria e o ano persistidos devolvem o centavo exato, a comparação entre anos e o documento pelo número.
- **`AC-089`**: categoria inexistente com instrução embutida permanece inconclusiva e não repete o valor inventado; termo vedado recebe HTTP 422.
- **`AC-090`**: a pergunta sobre pendências e a pergunta sobre regra sem dossiê público não revelam o título da triagem interna.
- **`AC-091`**: as rotas HTTP existem e o wireframe identifica a série ilustrativa e os endpoints.

## 13. Dependências
- `SPEC-0001`, `SPEC-0003`, `SPEC-0004`, `SPEC-0021`
- SQLite local de `CivicLakehouseStorage`
- Nenhuma credencial externa

## 14. Riscos e Limitações
- O classificador de intenção é lexical. Perguntas fora dos padrões documentados recebem inconclusão, não uma resposta inventada.
- O catálogo continua com `last_sync_utc` declarado. A cobertura não trata esse campo como coleta observada.
- Esta especificação não avalia qualidade de Laya nem de Jev sobre despesa pública.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_empty_lakehouse_coverage_is_zero_and_states_the_limitation`
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_persisted_expense_totals_reconcile_by_source_in_cents`
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_grounded_question_returns_category_total_from_stored_rows`
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_unknown_category_and_prompt_injection_stay_inconclusive`
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_public_pending_question_hides_internal_triage_title`
- `tests/test_public_coverage_and_grounded_questions.py::TestPublicCoverageAndGroundedQuestions::test_http_routes_and_wireframe_label_sample_figures`

## 16. Questões Pendentes
- A consulta de marca no INPI permanece aberta e não bloqueia este incremento, porque o nome Verba Clara não foi adotado.
- Não há projeto Supabase vinculado nesta execução. O contrato usa o SQLite já existente.

# SPEC-0023 — Protocolo público de contestação

## 1. Identificador e Título
- **ID:** `SPEC-0023`
- **Título:** Protocolo público de contestação sem publicação automática do texto

## 2. Status e Versão
- **Status:** `Verificado` em 26 de outubro de 2026, 21:11 (America/Sao_Paulo): 140 testes e harness checkpoint 4 com 3 tentativas (`pass_at_1` 1.0, `pass_hat_k` 1.0)
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Quem encontra erro factual, dado pessoal, problema de direito autoral, texto que precisa de revisão, crítica de método ou pedido de autoridade precisa de um protocolo rastreável. Esse fluxo é distinto do direito de resposta já ligado a um dossiê publicado. O texto do pedido não pode ir ao ar sozinho nem apagar a trilha.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Receber sete categorias de pedido e devolver um protocolo.
- Guardar o texto só para revisão autenticada, com CPF válido mascarado.
- Registrar meta interna de triagem e decisões em eventos imutáveis.

### Não-Objetivos
- Cumprir prazo legal ou produzir decisão jurídica.
- Publicar o texto do solicitante.
- Apagar dossiê, despesa ou trilha editorial.
- Operar plantão humano. O software registra; pessoas decidem.

## 5. Atores e Permissões
- `public_reader`: cria protocolo e consulta estado, categoria e datas.
- `reviewer_admin`: lê o texto e acrescenta decisão, com token.

## 6. Fluxos Principais
1. `POST /api/v1/challenges` grava status `RECEBIDO`, mesmo se o cliente enviar outro status.
2. `GET /api/v1/challenges/{id}` devolve o estado público, sem o texto.
3. `POST /api/v1/admin/challenges/decide`, com token, muda o status e acrescenta um evento.

## 7. Cenários Alternativos e de Erro
- Categoria desconhecida, texto vazio ou contato que não é e-mail: HTTP 422.
- Protocolo inexistente: HTTP 404.
- Token ausente na leitura integral ou na decisão: HTTP 403.
- Nota de decisão com linguagem vedada: HTTP 422, sem gravar a nota e sem ecoar o termo.
- Tentativa de alterar o texto recebido ou apagar o protocolo: o SQLite aborta a operação.

## 8. Requisitos Funcionais
- **`FR-051`**: o sistema registra contestação nas categorias `ERRO_FACTUAL`, `DOCUMENTO_INCORRETO`, `DADO_PESSOAL`, `DIREITO_AUTORAL`, `ALEGACAO_DIFAMATORIA`, `METODOLOGIA` e `SOLICITACAO_LEGAL`, sempre em `RECEBIDO`.
- **`FR-052`**: revisor autenticado acrescenta `EM_ANALISE`, `AGUARDANDO_COMPLEMENTO`, `DECIDIDO` ou `ESCALADO_JURIDICO` em evento novo, sem reescrever o texto recebido.

## 9. Requisitos Não Funcionais
- **`NFR-026`**: categorias urgentes (`DADO_PESSOAL`, `ALEGACAO_DIFAMATORIA`, `SOLICITACAO_LEGAL`) recebem meta interna de 2 dias corridos; as demais, 15 dias corridos. A resposta declara que isso não é prazo legal.

## 10. Regras de Negócio e Dados
- **`DATA-025`**: `statement_text`, categoria, referência, instante de recebimento e hash não mudam. Eventos não aceitam atualização nem exclusão. O protocolo não pode ser apagado.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-026`**: a resposta pública não inclui o texto nem o contato. CPF válido no texto é mascarado antes da gravação. A leitura integral exige `X-Admin-Token`. A política SQL de referência impede leitura anônima da tabela-base e só permite inserção pública em `RECEBIDO`.

## 12. Critérios de Aceite
- **`AC-092`**: pedido com CPF e status `DECIDIDO` nasce `RECEBIDO`, mascara o CPF e usa meta de 2 dias.
- **`AC-093`**: a leitura pública não contém o texto, inclusive quando ele cita termo vedado.
- **`AC-094`**: a decisão acrescenta evento e o banco recusa alteração ou exclusão do conteúdo recebido.
- **`AC-095`**: nota vedada não é gravada; contato que não é e-mail é recusado; metodologia usa meta de 15 dias.
- **`AC-096`**: as rotas HTTP exigem token para o registro integral.
- **`AC-097`**: o wireframe oferece o formulário e o SQL de referência nomeia as políticas novas.

## 13. Dependências
- `SPEC-0003`, `SPEC-0004`, `SPEC-0022`
- SQLite local. O arquivo `rls_policies.sql` não está aplicado a um projeto Supabase.

## 14. Riscos e Limitações
- A meta de dias corridos não conta feriado nem expediente.
- Não há equipe designada para cumprir a meta.
- O formulário não substitui ordem judicial nem direito de resposta de dossiê já publicado.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_public_challenges.py::TestPublicChallenges::test_submission_masks_cpf_and_starts_received`
- `tests/test_public_challenges.py::TestPublicChallenges::test_public_read_hides_statement_even_when_it_quotes_a_forbidden_term`
- `tests/test_public_challenges.py::TestPublicChallenges::test_decision_appends_event_and_received_text_cannot_be_rewritten_or_deleted`
- `tests/test_public_challenges.py::TestPublicChallenges::test_decision_note_rejects_forbidden_language_and_invalid_contact`
- `tests/test_public_challenges.py::TestPublicChallenges::test_http_routes_require_admin_token_for_the_full_record`

## 16. Questões Pendentes
- Quem opera a fila humana e em qual canal recebe o e-mail ainda não está definido. O campo de contato fica armazenado e fora da resposta pública.

# Modelo de ameaças

Avaliação de engenharia para o aplicativo local e a API já existentes. Não substitui teste de invasão.

## Ativos

- Lotes brutos e hashes.
- Registros curados com nomes de agentes públicos no exercício da função e documentos de fornecedores.
- Dossiês em triagem, invisíveis ao leitor público.
- Token administrativo comparado com `hmac.compare_digest`.
- Chaves de fonte, hoje apenas previstas em variável de ambiente.

## Atores

Leitor anônimo, revisor com token, operador do ambiente e conteúdo não confiável vindo de portal oficial ou de formulário.

## Abusos considerados

| Ameaça | Controle presente | Residual |
| :--- | :--- | :--- |
| Leitura de dossiê em triagem | Filtro por papel e política SQL de referência | A política Supabase não está aplicada a um projeto remoto |
| Injeção de instrução em texto de nota ou pergunta | `sanitize_untrusted_text` | O classificador de perguntas é lexical e pode errar a intenção; a falha esperada é inconclusão, não obediência à instrução |
| Linguagem de acusação automática | `assert_non_accusatory_language` em sinais, respostas e perguntas | A lista não é o conjunto completo da língua portuguesa |
| SSRF na coleta | `http_client.py` restringe esquema e hospedeiros | Depende do uso desse cliente em toda coleta nova |
| Estouro de pedido | Limite em memória por IP, padrão 60 em 60 segundos | O contador não é compartilhado entre processos |
| Token no repositório | `.env.example` sem segredo; CI com `contents: read` | Um contribuidor ainda pode commitar segredo se o gancho local não impedir |
| Cifra ilustrativa lida como fato | Rótulo de amostra e cobertura calculada | Quem copiar só o cartão antigo ainda vê a série de desenho, agora rotulada |
| Pedido de dado pessoal completo | Recusa na pergunta pública; CPF mascarado na ingestão | Dados de função pública que a fonte já publica continuam necessários para entender o gasto |

## Fora do modelo desta rodada

Não houve varredura dinâmica contra um deploy, nem análise de cluster Kubernetes. Não há cluster.

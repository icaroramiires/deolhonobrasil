# Runbooks

Procedimentos do ambiente local. Nenhum passo abaixo cria recurso na nuvem.

## Subir testes

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Amostra local do pipeline

```bash
PYTHONPATH=src python3 -m deolhonobrasil.pipeline.cli run-sample --verify-reconciliation
```

A amostra não é uma coleta nacional. Os totais dela são os registros do fixture.

## Harness

```bash
PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 4 --trials 3
```

## Docker

`docker compose` usa o serviço definido em `docker-compose.yml`. Não inclui banco Supabase. Variáveis sensíveis ficam fora da imagem.

## Encerrar

Interromper o processo do servidor local. Apagar o diretório de dados de teste não apaga o código. Não há volume de produção gerido por este repositório.

## Falha de fonte

Se um conector passar a receber esquema diferente, o registro inválido vai para quarentena ou a execução falha de forma visível. Não corrigir o bruto em silêncio. Guardar o hash do payload que falhou.

## Incidente de dado pessoal

1. Parar a publicação do endpoint afetado.
2. Manter o lote bruto e o hash.
3. Corrigir a máscara na ingestão e reprocessar a camada curada sem alterar o bruto.
4. Registrar a retificação na trilha editorial quando houver dossiê.

## Pedido legal

Preservar evidência, não apagar trilha e encaminhar a quem representa o operador. Este runbook não autoriza cumprimento automático de remoção.

## Supabase, Jira e Confluence

Não há runbook de produção para esses serviços porque não há projeto autenticado nesta execução. O Atlassian MCP pediu autenticação. O MCP GitHub falhou na descoberta. O `gh` em modo leitura consultou o repositório público `icaroramiires/deolhonobrasil`.

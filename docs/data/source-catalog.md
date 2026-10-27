# Catálogo de fontes

O catálogo executável está em `get_official_data_source_catalog`, exposto em `GET /api/v1/sources/catalog`. A resposta inclui `catalog_last_sync_is_declared_metadata: true`. O campo `last_sync_utc` de cada item é texto mantido no código. Ele não prova que esta máquina coletou a fonte nesse instante.

A cobertura observada, `GET /api/v1/public-coverage`, lista `observed_sources` a partir das linhas e `catalog_source_ids_without_local_rows` quando o identificador do catálogo não aparece no SQLite.

## Fontes com conector no repositório

| Identificador | Órgão | Acesso verificado na documentação do projeto | Licença de reúso |
| :--- | :--- | :--- | :--- |
| `CAMARA_CEAP` | Câmara dos Deputados | API e arquivos anuais descritos em `.env.example` | Dado oficial. Redistribuição derivada segue `LICENSE` somente com atribuição e proveniência. O termo específico de cada arquivo precisa ser relido na fonte antes de um espelho público |
| `SENADO_CEAPS` | Senado Federal | CSV anual descrito em `.env.example` | Idem |
| `CGU_EMENDAS` | Portal da Transparência | API exige chave gratuita pedida pelo órgão. A variável `CGU_API_KEY` está vazia no exemplo | Idem. Chave não vai para o navegador nem para a imagem |
| `PNCP_CONTRATOS` | PNCP | URL de consulta em `.env.example` | Idem |
| `CGU_CEIS_CNEP` no enum; `CGU_CEIS` e `CGU_CNEP` no catálogo | CGU | Conector de sanções no código | Os identificadores do catálogo e do enum não são o mesmo literal. A cobertura trata diferença de identificador como fonte sem linha daquele `source_id` |

## Fontes citadas no catálogo e ainda dependentes de carga

`TSE_ELEICOES` e `RECEITA_FEDERAL_CNPJ` têm metadados e modelos usados por regras quando há registros de teste. Isso não equivale a uma carga nacional contínua neste ambiente.

## Fontes adiadas

TCU, portais estaduais e municipais, Compras.gov.br, Transferegov, diários oficiais e PDF escaneado ficam fora até existir conector, amostra, termo de uso e teste de contrato próprios.

## O que cada ingestão já guarda

Quando um conector persiste lote, o manifesto guarda fonte, URL, instante de coleta, caminho do bruto, tamanho e SHA-256. O registro curado aponta para esse hash. Valor monetário ausente não vira zero; o registro vai para quarentena.

## Formatos

JSON, CSV e respostas de API estruturada estão no caminho atual. XLS, PDF, DOC, imagem e arquivos compactados não têm extrator genérico implementado. Um arquivo compactado só deve entrar com limite de tamanho, tipo real verificado e proibição de caminho que escape do diretório de trabalho. Esse extrator ainda não existe.

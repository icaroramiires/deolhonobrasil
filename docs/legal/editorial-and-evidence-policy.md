# Política editorial e de evidências

Política operacional do software. Não é aconselhamento jurídico.

## Separação

Toda saída relevante distingue:

1. Informação verificada nas linhas ou no documento citado.
2. Divergência entre fontes.
3. Anomalia estatística diante de um conjunto de comparação declarado.
4. Inconsistência documental.
5. Indício que pede verificação adicional.
6. Item em revisão humana.
7. Análise inconclusiva.
8. Encerramento sem irregularidade demonstrada, somente após revisão.
9. Encaminhamento a órgão, somente quando o encaminhamento tiver ocorrido e estiver registrado. O software não cria esse encaminhamento sozinho.

A enumeração `EpistemicClassification` já cobre parte desses estados. Onde o código ainda usa rótulos mais antigos, a interface e as respostas novas não podem comprimi-los numa nota de culpabilidade.

## Conduta

- Título neutro e descrição do que o dado mostra.
- Link ou identificador da fonte e hash do lote quando o registro passou pelo lakehouse.
- Método nomeado: regra, SQL ou revisão humana.
- Limitação e hipótese alternativa quando o sinal não esgota a explicação.
- Canal de correção pelo direito de resposta já implementado.
- Correção deixa rastro. A API pública não apaga `editorial_audit_trail`.

## Proibições

Não publicar, com base em escore ou denúncia não verificada, as fórmulas “fraude comprovada”, “corrupto”, “crime cometido” ou equivalentes. Ausência de prova não é prova de inocência nem de culpa.

Nenhum achado sensível produzido só por modelo segue para o leitor público. No código, score igual ou acima de 0,70 ou sinal nominal segue para revisão.

## Contestação

O protocolo de direito de resposta recebe o pedido, sanitiza o texto e pode ser exibido ao lado do dossiê publicado. Fluxos separados para erro factual, dado pessoal, direito autoral, alegação difamatória, crítica de método e ordem judicial ainda precisam de procedimento humano com prazo e responsável. O software não autoriza o usuário a editar a trilha.

## Direito de resposta e censura

A manifestação publicada não apaga o fato documentado. Ela fica visível com o mesmo destaque exigido por `equal_visual_prominence`. Remoção de conteúdo só entra no estado de retificação quando um revisor autenticado registra o erro material.

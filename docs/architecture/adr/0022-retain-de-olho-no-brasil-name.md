# ADR-0022 — Manutenção do nome De Olho no Brasil

- **Status:** Aceito
- **Data:** 2026-10-26
- **Contexto:** avaliação do nome de trabalho Verba Clara antes de qualquer rebranding

## Contexto

O pedido de planejamento usou **Verba Clara** como nome de trabalho. O repositório já publica o software, a marca nominativa e a política de identidade em `TRADEMARK.md` sob o nome **De Olho no Brasil**. A licença AGPL-3.0-or-later não cobre o nome.

## Evidência consultada

Em 26 de outubro de 2026, a página [https://verbaclara.pro/](https://verbaclara.pro/) descrevia o serviço VerbaClara como auditoria cidadã de verbas públicas. O rodapé associa o serviço a FISCOIA INOVA SIMPLES (I.S.), CNPJ 67.973.713/0001-02, Juazeiro do Norte/CE. O domínio, o objeto social aparente e o público se sobrepõem ao deste projeto.

A busca pública de marcas do INPI (`https://servicos.busca.inpi.gov.br/marcas`) é uma aplicação interativa. Esta execução não obteve um resultado de processo marcário. A ausência dessa consulta não torna o nome disponível.

Uma busca de repositórios GitHub pelo termo `verbaclara` não retornou itens nesta execução. Isso não afasta o conflito do serviço já publicado na web.

## Decisão

Em 26 de outubro de 2026, por volta das 19:15 (America/Sao_Paulo), o mantenedor confirmou: manter o nome **De Olho no Brasil**.

1. O produto, o pacote Python `deolhonobrasil`, a interface, a API e a documentação institucional continuam com esse nome.
2. Verba Clara não é nome deste software. A menção a esse termo fica restrita a este registro e aos documentos que explicam por que ele não foi adotado.
3. Nenhuma alternativa de nome foi escolhida. Uma troca futura exige pedido explícito, nova busca de marca e domínio e atualização de `TRADEMARK.md`.

## Consequências

Não há rebranding de pacote, rotas, testes ou interface. Uma troca futura de nome exige nova busca de marca, domínio e conflito com iniciativas existentes, além de atualização expressa de `TRADEMARK.md`.

## Alternativas consideradas

- Adotar Verba Clara: rejeitada pelo conflito verificado em `verbaclara.pro`.
- Criar um segundo produto com outro nome dentro deste repositório: rejeitada. Duplicaria identidade, licença de marca e superfície jurídica sem ganho funcional.

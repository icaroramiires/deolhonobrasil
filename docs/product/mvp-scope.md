# Escopo do MVP

O recorte histórico está em [`mvp.md`](mvp.md). Este arquivo fixa o que está dentro e fora do produto depois da avaliação de nome e da cobertura observada.

## Dentro do MVP atual

1. Quatro famílias de dado federal estruturado: CEAP, CEAPS, emendas do Portal da Transparência e contratos PNCP, mais sanções CEIS/CNEP e cadastros usados nas regras já testadas.
2. Preservação do bruto, hash SHA-256, idempotência e reconciliação em centavos.
3. Regras determinísticas versionadas nas especificações `SPEC-0002` e `SPEC-0007` a `SPEC-0018`.
4. Publicação nominal apenas depois de revisor identificado.
5. API local e wireframe. A partir de `SPEC-0022`, a cobertura numérica do ambiente é calculada do SQLite; os milhões do gráfico permanecem amostra ilustrativa.

## Fora do MVP

- Todas as esferas e todos os municípios ao mesmo tempo.
- Leitura de PDF escaneado como se fosse texto confiável.
- Ranking de pessoas ou nota única de culpabilidade.
- Adoção do nome Verba Clara.
- Deploy de produção, Supabase gerenciado e Terraform apply.

## Próximo conector, quando houver autorização de custo e rede

O candidato seguinte continua sendo uma fonte oficial já prevista no catálogo e ainda sem linha local no ambiente de quem executa a coleta. A escolha depende de termo de uso, chave quando a fonte exigir, e de um teste de contrato com amostra real. Esta alteração não executou essa coleta.

## Premissa de custo

Desenvolvimento e teste locais não adicionam fatura de nuvem. Não há cotação anexada de Cloud Run, Supabase ou armazenamento objeto. Qualquer número de preço precisa ser lido da calculadora do provedor no momento de um deploy autorizado. Nenhum recurso pago foi criado aqui.

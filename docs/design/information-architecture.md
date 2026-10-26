# Arquitetura de informação

## Navegação principal

1. Visão geral
2. Pesquisa
3. Despesas
4. Contratos
5. Análises
6. Evidências
7. Acompanhamentos

## Navegação secundária planejada

- Perfis: fornecedores, representantes e órgãos.
- Contribuição cidadã e solicitações.
- Metodologia, fontes e transparência.
- Conta, segurança e preferências.
- Administração.

## Hierarquia de entidades

- Órgão → despesas, contratos, licitações, documentos e análises.
- Fornecedor → contratos, pagamentos, órgãos relacionados e evidências.
- Representante → mandato, emendas, destinações e fontes.
- Contrato → licitação, fornecedor, órgão, aditivos, pagamentos e documentos.
- Despesa → empenho, liquidação, pagamento, favorecido, órgão e fonte.
- Análise → método, sinal, evidências, limitações, revisão e contestação.
- Dossiê → documentos, linha do tempo, entidades e relações comprovadas.

## Modelo de navegação

- Busca global disponível em todas as páginas.
- Listas conduzem a detalhes; detalhes conduzem a fontes e evidências.
- Breadcrumbs em níveis de terceiro grau ou superiores.
- A ação “Acompanhar” deve preservar contexto e confirmar frequência.
- Retorno mantém termo, filtros, ordenação e posição da lista.

## Papéis e permissões

| Papel | Consultar | Salvar/alertar | Contribuir | Contestar | Revisar/publicar | Administrar ingestão |
|---|---:|---:|---:|---:|---:|---:|
| Visitante | Sim | Não | Sim | Sim | Não | Não |
| Usuário | Sim | Sim | Sim | Sim | Não | Não |
| Colaborador | Sim | Sim | Sim | Sim | Rascunhos | Não |
| Editor | Sim | Sim | Sim | Sim | Sim | Não |
| Administrador | Sim | Sim | Sim | Sim | Sim | Sim |

Solicitações sem permissão devem explicar o motivo e oferecer login ou pedido de acesso, sem apagar o trabalho já preenchido.

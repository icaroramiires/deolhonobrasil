# ADR 0020 — Perfis Cívicos de Entidades (Fornecedor, Mandatário e Órgão), Modais de Detalhe P0 e Linha do Tempo de Aditivos

## Status
Aprovado

## Data
2026-10-26

## Contexto
Com a entrega do Design System Unificado na `SPEC-0019`, a interface cívica do **De Olho no Brasil** consolidou as 7 visões de navegação P0 e conformidade de acessibilidade WCAG 2.2 AAA. No entanto, conforme especificado no pacote de design em `docs/design/screens.md` (P0 Detalhes e P1 Perfis) e `docs/design/flows.md` (Jornadas 1, 2 e 3):

1. **Investigação em Profundidade de Entidades Cívicas (P1):**
   - O cidadão ou jornalista de dados que clica em um fornecedor, parlamentar ou órgão público precisa de um painel de perfil consolidado que reúna identificação cadastral oficial (RFB/TSE/Portal da Transparência), endereço físico, Quadro de Sócios e Administradores (QSA), histórico de contratos e pagamentos acumulados, doações de campanha vinculadas e eventuais sinais/sanções ativas;
   - As entidades devem ser segregadas em 3 arquétipos fundamentais:
     - **Perfil de Fornecedor (PJ/PF):** CNPJ/Razão Social, Nome Fantasia, situação cadastral, capital social declarado e razão frente a contratos, CNAE principal e secundários, endereço físico, sócios administradores (QSA), contratos ativos, total recebido e histórico de sanções (CEIS/CNEP);
     - **Perfil de Representante Público (Mandatário/Parlamentar):** Identificação oficial, mandato, partido, UF, cotas CEAP/CEAPS discriminadas por subcota (passagens, combustíveis, consultoria, divulgação), emendas parlamentares destinadas com distinção de valor empenhado vs pago, e doações eleitorais declaradas de fornecedores contratados (TSE);
     - **Perfil de Órgão Público:** CNPJ, esfera, competências, orçamento executado, total de contratos (PNCP), fornecedores dominantes (Índice HHI) e índice de completude/qualidade dos dados.

2. **Modais e Telas de Detalhes P0 com Decomposição Epistêmica e Linha do Tempo:**
   - **Detalhe de Despesa:** Apresentação discriminada dos 3 estágios contábeis (Empenhado, Liquidado e Pago), reconciliação matemática comprovada, número da nota/documento fiscal, favorecido, órgão contratante, link para o portal oficial e hash canônico `SHA-256`;
   - **Detalhe de Contrato:** Linha do tempo interativa de termos aditivos (data, acréscimo de valor, prorrogação de vigência e justificativa), comparação clara entre valor inicial homologado vs valor atualizado vs valor total pago, objeto contratual completo e documentos anexos;
   - **Detalhe de Análise:** Apresentação contextualizada do sinal de auditoria com resumo claro, método estatístico/determinístico, evidências favoráveis e contrárias, limitações expressas, explicações alternativas legítimas, auditor humano responsável e protocolo de contestação cidadã.

3. **Acessibilidade e Usabilidade dos Modais (WCAG 2.2 AA):**
   - Fechamento imediato por tecla `Esc` e botão de fechar acessível;
   - Armadilha de foco por teclado (*focus trap*) impedindo que o cursor escape para o fundo da página enquanto o modal estiver ativo;
   - Atributos semânticos `role="dialog"`, `aria-modal="true"` e `aria-labelledby`;
   - Retorno automático de foco para o elemento disparador ao fechar o modal.

## Decisão
1. **Estrutura dos Componentes e Endpoints de Perfis e Detalhes:**
   - Adicionar ao servidor WSGI `CivicAuditHTTPApp` as rotas de agregação de perfil e detalhes:
     - `GET /api/v1/entities/supplier?doc=<cnpj_ou_cpf>`: Retorna dados cadastrais, QSA, despesas/contratos agregados e sanções;
     - `GET /api/v1/entities/agent?id=<agent_id>`: Retorna mandato, subcotas CEAP/CEAPS, emendas parlamentares e doações do TSE;
     - `GET /api/v1/entities/organ?id=<organ_code>`: Retorna despesas totais, contratos PNCP e índice HHI de concentração de fornecedores;
     - `GET /api/v1/details/contract?id=<contract_id>`: Retorna detalhe completo do contrato com array de aditivos em ordem cronológica;
     - `GET /api/v1/details/expense?id=<expense_id>`: Retorna detalhe da despesa com os 3 estágios contábeis e comprovante fiscal.
   - Fornecer payload de dados em memória para funcionamento offline/sandbox imediato caso a entidade consultada esteja presente nos lotes locais.

2. **Renderização de Modais Acessíveis e Linha do Tempo em CSS Nativo:**
   - Implementar container de modal acessível com `.civic-modal-backdrop` e `.civic-modal-dialog` estruturados com classes utilitárias do Design System;
   - Linha do tempo de termos aditivos estruturada em lista ordenada (`<ol class="timeline-list">`) com indicadores cronológicos visuais e textuais;
   - Navegação cruzada fluida: clicar em qualquer CNPJ abre o modal de Fornecedor; clicar no nome do parlamentar abre o modal de Representante; clicar no órgão abre o modal de Órgão.

3. **Governança Epistêmica e Não-Acusatória:**
   - Toda alteração contratual (aditivo) deve ser explicada como instrumento legal regular previsto na Lei nº 14.133/2021;
   - Doações eleitorais declaradas devem carregar limitação expressa de legalidade;
   - Zero termos acusatórios ou conclusões sancionatórias prematuras.

## Consequências
### Positivas
- Cumpre integralmente os requisitos de telas P0 e perfis P1 do handoff de design (`docs/design/screens.md`).
- Aumenta expressivamente o poder investigativo do cidadão ao permitir navegação cruzada entre tabelas, perfis e linhas do tempo.
- Totalmente acessível (teclado, leitor de tela, WCAG 2.2 AA).
- Funciona 100% offline no servidor WSGI autocontido.

### Negativas / Mitigações
- Aumento moderado na complexidade do DOM e JavaScript de renderização. A mitigação consiste em reutilizar o mesmo esqueleto de modal para os 4 tipos de visualização (Fornecedor, Representante, Órgão e Detalhe), injetando o conteúdo dinamicamente com sanitização estrita.

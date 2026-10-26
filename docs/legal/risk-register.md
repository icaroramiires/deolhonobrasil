# Registro de riscos jurídicos e de privacidade

Matriz para revisão por profissional habilitado. Não é parecer jurídico. Probabilidade e impacto abaixo são juízos de engenharia, em escala baixa, média ou alta, para orientar controle. Não são frequências medidas.

Legislação a reler no texto oficial vigente, sem extrair daqui uma interpretação de caso:

- Constituição Federal, em especial liberdade de expressão e proteção da honra, da imagem, da intimidade e da vida privada.
- Lei nº 12.527/2011, Lei de Acesso à Informação.
- Lei nº 13.709/2018, Lei Geral de Proteção de Dados Pessoais.
- Lei nº 12.965/2014, Marco Civil da Internet, quando houver aplicação a provedor.
- Lei nº 9.610/1998, direitos autorais, e os termos de cada fonte de dados.
- Código Civil, responsabilidade civil e dever de não causar dano.
- Regras processuais de preservação de prova e de cumprimento de ordem judicial, no momento em que um caso concreto existir.

| ID | Risco | Prob. | Impacto | Controle já presente | Residual |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R-01 | Texto automatizado ser lido como acusação de crime | Média | Alto | Bloqueio de termos, três camadas epistêmicas, revisão antes da publicação nominal | Linguagem pode ser ofensiva sem usar a lista fechada |
| R-02 | Conflito de nome com iniciativa existente | Alta para Verba Clara | Alto | ADR-0022 recusa o nome | Busca de marca no INPI ainda não foi concluída para o nome atual |
| R-03 | Tratar dado oficial como livre de qualquer restrição | Média | Alto | `LICENSE` separa código, dado derivado e marca | Termo de cada arquivo oficial precisa ser relido antes de espelho em massa |
| R-04 | Exposição de CPF ou endereço | Média | Alto | Máscara na ingestão e recusa de pedido de desmascaramento na pergunta pública | Fonte pode publicar outros identificadores de função pública |
| R-05 | Cifra falsa ou desatualizada | Média | Alto | Cobertura calculada do lakehouse e rótulo de amostra no wireframe | Catálogo ainda declara `last_sync_utc` fixo |
| R-06 | Direito de resposta virar censura ou ser ignorado | Média | Alto | Protocolo técnico lado a lado e trilha append-only | Não há equipe de plantão nem prazo interno ensaiado com pessoas |
| R-07 | Ordem judicial ou pedido de remoção sem trilha | Baixa no MVP local | Alto | Trilha editorial não é apagada pela API pública | Falta procedimento operacional nomeado |
| R-08 | Licença AGPL interpretada como escudo contra ação civil | Média se houver comunicação imprecisa | Alto | `LICENSE` diz que a licença não é imunidade | Mantenedores continuam expostos por ato próprio, fora do direito autoral |
| R-09 | Uso político-partidário da marca | Média | Alto | `TRADEMARK.md` veda esse uso | Fiscalização da marca depende dos titulares |

Responsável por aceitar risco residual de publicação na internet: os mantenedores do repositório, com revisão jurídica própria. Esta execução não nomeia uma pessoa como operador de produção.

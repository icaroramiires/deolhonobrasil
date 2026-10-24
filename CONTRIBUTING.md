# Diretrizes de Contribuição e Política Editorial (`CONTRIBUTING.md`)

Bem-vindo(a) à comunidade **De Olho no Brasil**! Toda contribuição de código, conectores de dados, regras de auditoria ou documentação deve respeitar rigorosamente nossa **Política Editorial Baseada em Evidências**.

## 1. Regras Inegociáveis para Contribuidores
1. **Anomalia Estatística $\neq$ Irregularidade ou Crime:** Nenhum código, variável, mensagem de interface, prompt ou documentação pode rotular automaticamente uma divergência de dados como `"fraude"`, `"corrupção"`, `"roubo"` ou `"crime"`. Use a taxonomia epistêmica oficial (`FATO_DOCUMENTADO`, `DIVERGENCIA_ENTRE_BASES`, `SINAL_ESTATISTICO`, `ESCLARECIMENTO_SOLICITADO`).
2. **Proveniência Obrigatória (`100% Rastreável`):** Nenhum conector ou transformação pode inserir registros na camada `Curated` sem preencher `source_name`, `source_url`, `collected_at` e `raw_sha256`.
3. **Hipóteses Alternativas Obrigatórias:** Toda regra determinística ou estatística proposta deve documentar explicitamente quais cenários administrativos legítimos ou erros materiais da fonte podem gerar aquele sinal (causas de falsos positivos).
4. **Neutralidade Política e Institucional:** Regras e modelos devem ser 100% cegos a partido político, espectro ideológico ou unidade federativa.
5. **Testes como Evidência:** Nenhuma Pull Request será aceita sem testes automatizados (`pytest`) cobrindo casos normais, casos de borda, entradas malformadas (quarentena) e reconciliação de somatórios.

## 2. Fluxo de Desenvolvimento Local
```bash
# Executar a suíte de testes da fundação e do pipeline de dados:
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

# Portões de qualidade

O harness em `src/deolhonobrasil/harness/runner.py` verifica pacotes de especificação, âncoras de teste e um mínimo de testes que não pode cair. O mínimo atual do código é 140, depois da inclusão de `SPEC-0022` e `SPEC-0023`.

O workflow `.github/workflows/ci.yml` executa, em pull request e nas branches `main` e `develop`:

1. `unittest discover`
2. `scripts/run_security_audit.py`
3. `scripts/run_loop.py status`
4. harness com checkpoint 4 e 3 tentativas

## O que este repositório ainda não liga no CI

- Lint obrigatório, embora `ruff` esteja nas extras de desenvolvimento.
- Verificação de tipo obrigatória, embora `mypy` esteja nas extras.
- Playwright.
- Scanner de dependências, CodeQL e Dependabot.
- `terraform fmt` e `terraform validate`, porque não há módulos Terraform.
- Deploy. Publicação em homologação ou produção é etapa separada e não existe neste workflow.

## Regra contra métrica vazia

Um portão só é descrito como verde depois de executado na árvore corrente. Contagens antigas em `.agents/loop/state.json` são evidência de uma execução anterior, não desta alteração, até que o comando seja rodado de novo.

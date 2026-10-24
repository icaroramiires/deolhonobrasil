# De Olho no Brasil — Estratégia de Testes e Qualidade (TDD + Eval Harness)

**Versão:** 1.0.0  
**Referências SDD:** `SPEC-0001..0004`, `docs/LOOP_ENGINEERING_SDD_HARNESS.md`

---

## 1. Pirâmide de Verificação e Testes

1. **Testes Unitários de Domínio e Privacidade (`tests/test_foundation_and_pipeline.py`):**
   - Validação de CNPJ (Módulo 11), mascaramento LGPD de CPF (`***.XXX.XXX-**`), bloqueio de conversão de valor nulo em zero (`MonetaryParseError`), sanitização de *prompt injection* e bloqueio de termos acusatórios.
2. **Testes Estatísticos, Regras Determinísticas e IA (`tests/test_audit_and_governance.py`):**
   - Exatidão matemática de `calculate_z_score`, `calculate_mad_z_score`, `calculate_hhi_concentration` e `evaluate_benford_first_digit`.
   - Avaliação das regras `R-PNCP-OVERPRICE-Z3`, `R-CGU-HHI-CONCENTRATION` e `R-CEAP-OUTLIER-Z3`.
   - Calibração do `LayaSystem1Adapter` (garantindo que scores $\ge 0.70$ exijam `REVISAO_HUMANA`) e `GroundedDossierNarrator` (recusa sem `provenance_hashes`).
3. **Testes de Integração Lakehouse, Governança e RLS (`tests/test_foundation_and_pipeline.py` & `tests/test_audit_and_governance.py`):**
   - Idempotência de ingestão SQLite/Parquet, reconciliação financeira exata (`difference == Decimal("0.00")`), visibilidade por perfil (`PUBLIC_READER` vs `REVIEWER_ADMIN`), Direito de Resposta lado a lado, retificação de erro material e imutabilidade da tabela `editorial_audit_trail`.
4. **Testes de Contrato SDD, GateGuard e UI (`tests/test_harness.py`):**
   - Verificação automática dos pacotes `docs/specs/SPEC-0001..0004/`, resolução dos *Test Anchors*, checagem de `frozen=True` nas entidades de domínio e invariantes estruturais da UI `achromatic-ledger`.
5. **Inspeção Visual e E2E (`lint.mjs`, `inspect.mjs`, `agent-browser`):**
   - Auditoria estática e em navegador headless Chromium nos viewports `1440x900`, `768x1024` e `390x844`.

---

## 2. Comandos Oficiais de Execução

```bash
# 1. Suíte completa de testes unitários e de integração (43 testes)
PYTHONPATH=src python3 -m unittest discover -s tests -v

# 2. Verification Loop completo (6 fases + SDD Traceability + GateGuard + 3 trials Eval Harness)
PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3
```

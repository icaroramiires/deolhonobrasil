# De Olho no Brasil

> **Infraestrutura cívica aberta de transparência pública, rastreabilidade de dados oficiais e auditoria assistida.**
> *Princípio Central: A IA identifica sinais que merecem investigação; evidências verificáveis, análise qualificada e procedimentos adequados sustentam as conclusões.*

---

## 1. Visão Geral e Pilares Fundamentais

O **De Olho no Brasil** transforma dados públicos dispersos dos Poderes Executivo e Legislativo Federal em informações acessíveis, verificáveis e rastreáveis.

1. **Rastreabilidade (`100% Proveniência`):** Cada registro normalizado preserva o link oficial da fonte primária (`source_url`), o timestamp de coleta (`collected_at`) e o hash criptográfico (`SHA-256`) do lote original.
2. **Confiabilidade (`Zero Acusações Automáticas`):** O sistema separa fatos documentados, divergências entre bases e sinais estatísticos, exigindo hipóteses alternativas e oferecendo canal estruturado de Direito de Resposta e Correção.
3. **Acessibilidade e Proteção de Dados (`LGPD`):** Linguagem clara para qualquer cidadão, combinada com minimização e mascaramento automático de CPFs de pessoas físicas comuns (`***.XXX.XXX-**`).

---

## 2. Arquitetura do Repositório (Fases 1 e 2 Implementadas)

```text
deolhonobrasil/
├── .github/workflows/ci.yml              # Pipeline CI (Testes, Proveniência, Segurança)
├── src/deolhonobrasil/
│   ├── __init__.py
│   └── pipeline/
│       ├── __init__.py
│       ├── models.py                     # Contratos de Dados, Proveniência e Taxonomia Epistêmica
│       ├── privacy.py                    # Sanitização LGPD, Mascaramento CPF e Validação CNPJ/SHA-256
│       ├── quarantine.py                 # Gestão de Quarentena de Registros Inválidos
│       ├── storage.py                    # Camada Lakehouse Local (SQLite/DuckDB-ready + Manifesto Raw)
│       ├── reconciliation.py             # Reconciliação Contábil e Testes de Qualidade por Fonte
│       ├── cli.py                        # CLI Reproduzível de Ingestão e Verificação
│       └── connectors/
│           ├── __init__.py
│           ├── base.py                   # Interface Base Idempotente com Hash SHA-256
│           ├── camara_ceap.py            # Conector Câmara dos Deputados (CEAP CSV/JSON)
│           ├── senado_ceaps.py           # Conector Senado Federal (CEAPS CSV/JSON)
│           ├── cgu_transparencia.py      # Conector Portal da Transparência/CGU (Emendas + CEIS/CNEP)
│           └── pncp_contratos.py         # Conector PNCP (Contratos e Aditivos - Lei 14.133/2021)
├── tests/                                # Suíte Completa de Testes Automatizados
├── Dockerfile                            # Container non-root (UID 10001) reproduzível
├── docker-compose.yml                    # Orquestração local com privilégio mínimo
├── LICENSE                               # Código sob AGPL-3.0-or-later | Dados sob CC-BY-4.0
├── TRADEMARK.md                          # Política de proteção de marca e identidade editorial
├── SECURITY.md                           # Política de segurança e divulgação responsável
└── CONTRIBUTING.md                       # Regras editoriais e técnicas para colaboradores
```

---

## 3. Como Executar Localmente (Checkpoints das Fases 1 e 2)

### 3.1. Executar a Suíte de Testes Automatizados
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### 3.2. Executar o Fluxo Completo de Dados (Raw -> Standardized -> Curated + Reconciliação)
```bash
PYTHONPATH=src python3 -m deolhonobrasil.pipeline.cli run-sample --verify-reconciliation
```

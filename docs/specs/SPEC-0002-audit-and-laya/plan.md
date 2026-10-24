# Plan: SPEC-0002 — Motor de Auditoria e Laya System 1

## 1. Arquitetura dos Subsistemas
- **`statistics.py`**: Implementa Z-Score paramétrico, MAD, HHI e Lei de Benford.
- **`rules.py`**: Contém regras determinísticas de sobrepreço, concentração de fornecedores e desvios de cota com aplicação de linguagem não-acusatória.
- **`laya_engine.py`**: Motor `LayaSystem1Adapter` (implementando `DecisionEnginePort`) para triagem de severidade e roteamento para revisão humana.
- **`rag_narrator.py`**: Narrador grounded responsável pelos 3 blocos epistêmicos e validação rigorosa de proveniência por hash.

## 2. Estratégia de Migração e Testes
- Testes unitários e de integração cobrindo todas as suítes estatísticas e comportamentais do motor Laya.

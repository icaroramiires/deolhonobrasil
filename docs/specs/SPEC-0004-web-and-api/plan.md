# Design Técnico: SPEC-0004 — Interface e API

**Versão:** 1.0.0  
**Status:** Aprovado  

## 1. Visão Geral
Este documento especifica o design da interface web (`wireframe_de_olho_no_brasil.html` com seed `2125632542`) e da API REST FastAPI para o Checkpoint 3.

## 2. Componentes da API (`src/deolhonobrasil/api/`)
- **`main.py`**: Aplicação FastAPI com middlewares de segurança e CORS.
- **`routes/dossiers.py`**: Endpoints de consulta de dossiês publicados.
- **`routes/expenses.py`**: Endpoints de despesas públicas.
- **`routes/reconciliation.py`**: Relatórios de reconciliação financeira.
- **`routes/right_of_reply.py`**: Submissão de direito de resposta.

## 3. Interface `achromatic-ledger`
- Estilo monocromático estrito (`achromatic-ledger`).
- Alinhamento numérico com `font-variant-numeric: tabular-nums`.
- Verificação automatizada de somas via `console.assert` comparando linhas com o elemento `<tfoot>`.

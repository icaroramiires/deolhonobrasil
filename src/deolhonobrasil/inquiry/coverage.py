"""Cobertura observada e respostas determinísticas sobre registros já persistidos.

Nenhum total desta camada representa o gasto público nacional. Valores monetários
permanecem em centavos inteiros. Nenhum modelo de linguagem participa do cálculo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
import unicodedata

from deolhonobrasil.pipeline.models import (
    assert_non_accusatory_language,
    get_official_data_source_catalog,
)
from deolhonobrasil.pipeline.privacy import sanitize_untrusted_text
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_HEX64_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")
_DOC_RE = re.compile(r"\b(?:NF|DOC)[-A-Za-z0-9]{1,40}\b", re.IGNORECASE)
_RULE_RE = re.compile(r"\bR-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
_PUBLIC_DOSSIER_STATUSES = (
    "PUBLICADO_COM_REVISAO",
    "ESCLARECIDO_COM_PROVA",
    "ERRO_MATERIAL_RETIFICADO",
)

_CATALOG_SYNC_LIMITATION = (
    "Os campos last_sync_utc do catálogo de fontes são metadados declarados no código. "
    "Eles não comprovam uma coleta executada neste ambiente."
)
_NOT_NATIONAL_LIMITATION = (
    "Os totais abaixo usam somente registros persistidos neste lakehouse. "
    "Não representam o gasto público do Brasil."
)
_NOT_ADDITIVE_LIMITATION = (
    "Despesas, contratos, emendas e sanções são leituras separadas. "
    "Esses conjuntos não são somados entre si."
)


def cents_to_brl(cents: int) -> str:
    """Formata centavos inteiros como string BRL com duas casas, sem ponto flutuante."""
    value = Decimal(int(cents)).scaleb(-2)
    return f"{value:.2f}"


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.casefold()


def _ledger(
    *,
    record_count: int,
    amount_fields: dict[str, int],
    period_start: str | None,
    period_end: str | None,
    by_source: list[dict[str, object]],
    first_collected_at_utc: str | None,
    latest_collected_at_utc: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_count": record_count,
        "period_start": period_start,
        "period_end": period_end,
        "first_collected_at_utc": first_collected_at_utc,
        "latest_collected_at_utc": latest_collected_at_utc,
        "by_source": by_source,
    }
    payload.update(amount_fields)
    return payload


def _sum_group(rows: list[dict[str, object]], field: str) -> int:
    return sum(int(row[field]) for row in rows)


def build_public_coverage(storage: CivicLakehouseStorage) -> dict[str, object]:
    """Agrega somente linhas existentes. Um total zero indica ausência local de linhas."""
    with storage._connect() as conn:
        expense_groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source,
                       COUNT(*) AS record_count,
                       COALESCE(SUM(net_amount_cents), 0) AS net_amount_cents,
                       MIN(issue_date) AS period_start,
                       MAX(issue_date) AS period_end,
                       MIN(collected_at_utc) AS first_collected_at_utc,
                       MAX(collected_at_utc) AS latest_collected_at_utc
                FROM curated_expenses
                GROUP BY source
                ORDER BY source ASC
                """
            ).fetchall()
        ]
        contract_groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source,
                       COUNT(*) AS record_count,
                       COALESCE(SUM(current_amount_cents), 0) AS current_amount_cents,
                       MIN(signature_date) AS period_start,
                       MAX(signature_date) AS period_end,
                       MIN(collected_at_utc) AS first_collected_at_utc,
                       MAX(collected_at_utc) AS latest_collected_at_utc
                FROM curated_contracts
                GROUP BY source
                ORDER BY source ASC
                """
            ).fetchall()
        ]
        amendment_groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source,
                       COUNT(*) AS record_count,
                       COALESCE(SUM(committed_amount_cents), 0) AS committed_amount_cents,
                       COALESCE(SUM(paid_amount_cents), 0) AS paid_amount_cents,
                       MIN(year) AS period_start,
                       MAX(year) AS period_end,
                       MIN(collected_at_utc) AS first_collected_at_utc,
                       MAX(collected_at_utc) AS latest_collected_at_utc
                FROM curated_amendments
                GROUP BY source
                ORDER BY source ASC
                """
            ).fetchall()
        ]
        sanction_groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source,
                       COUNT(*) AS record_count,
                       MIN(collected_at_utc) AS first_collected_at_utc,
                       MAX(collected_at_utc) AS latest_collected_at_utc
                FROM curated_sanctions
                GROUP BY source
                ORDER BY source ASC
                """
            ).fetchall()
        ]
        quarantine_count = int(
            conn.execute("SELECT COUNT(*) FROM quarantine_records").fetchone()[0]
        )
        category_count = int(
            conn.execute(
                "SELECT COUNT(DISTINCT expense_category) FROM curated_expenses"
            ).fetchone()[0]
        )
        expense_scalar = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(net_amount_cents), 0) FROM curated_expenses"
        ).fetchone()
        contract_scalar = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(current_amount_cents), 0) FROM curated_contracts"
        ).fetchone()
        amendment_scalar = conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(committed_amount_cents), 0),
                   COALESCE(SUM(paid_amount_cents), 0)
            FROM curated_amendments
            """
        ).fetchone()

    expense_count = _sum_group(expense_groups, "record_count")
    expense_cents = _sum_group(expense_groups, "net_amount_cents")
    if expense_count != int(expense_scalar[0]) or expense_cents != int(expense_scalar[1]):
        raise RuntimeError("A soma por fonte das despesas não fecha com o total do lote.")
    contract_count = _sum_group(contract_groups, "record_count")
    contract_cents = _sum_group(contract_groups, "current_amount_cents")
    if contract_count != int(contract_scalar[0]) or contract_cents != int(contract_scalar[1]):
        raise RuntimeError("A soma por fonte dos contratos não fecha com o total do lote.")
    amendment_count = _sum_group(amendment_groups, "record_count")
    committed_cents = _sum_group(amendment_groups, "committed_amount_cents")
    paid_cents = _sum_group(amendment_groups, "paid_amount_cents")
    if (
        amendment_count != int(amendment_scalar[0])
        or committed_cents != int(amendment_scalar[1])
        or paid_cents != int(amendment_scalar[2])
    ):
        raise RuntimeError("A soma por fonte das emendas não fecha com o total do lote.")
    sanction_count = _sum_group(sanction_groups, "record_count")

    observed_sources = sorted(
        {
            str(row["source"])
            for row in (*expense_groups, *contract_groups, *amendment_groups, *sanction_groups)
        }
    )
    catalog_ids = [item.source_id for item in get_official_data_source_catalog()]
    catalog_without_rows = [source_id for source_id in catalog_ids if source_id not in observed_sources]

    limitations = [
        _NOT_NATIONAL_LIMITATION,
        _NOT_ADDITIVE_LIMITATION,
        _CATALOG_SYNC_LIMITATION,
        "Registros em quarentena ficam fora dos totais monetários.",
    ]
    if expense_count == 0:
        limitations.append(
            "O valor zero de despesas significa que não há despesa persistida neste ambiente. "
            "Não significa ausência de gasto público."
        )

    def _bounds(groups: list[dict[str, object]], start_key: str, end_key: str) -> tuple[str | None, str | None]:
        starts = [str(row[start_key]) for row in groups if row.get(start_key) is not None]
        ends = [str(row[end_key]) for row in groups if row.get(end_key) is not None]
        return (min(starts) if starts else None, max(ends) if ends else None)

    def _collected(groups: list[dict[str, object]]) -> tuple[str | None, str | None]:
        firsts = [str(row["first_collected_at_utc"]) for row in groups if row.get("first_collected_at_utc")]
        lasts = [str(row["latest_collected_at_utc"]) for row in groups if row.get("latest_collected_at_utc")]
        return (min(firsts) if firsts else None, max(lasts) if lasts else None)

    expense_period = _bounds(expense_groups, "period_start", "period_end")
    expense_collected = _collected(expense_groups)
    contract_period = _bounds(contract_groups, "period_start", "period_end")
    contract_collected = _collected(contract_groups)
    amendment_period = _bounds(amendment_groups, "period_start", "period_end")
    amendment_collected = _collected(amendment_groups)
    sanction_collected = _collected(sanction_groups)

    return {
        "product": "De Olho no Brasil",
        "currency": "BRL",
        "amount_unit": "centavos",
        "calculated_from": "lakehouse_local",
        "represents_national_spending": False,
        "ledgers_are_additive": False,
        "uses_language_model": False,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expenses": _ledger(
            record_count=expense_count,
            amount_fields={
                "net_amount_cents": expense_cents,
                "net_amount_brl": cents_to_brl(expense_cents),
            },
            period_start=expense_period[0],
            period_end=expense_period[1],
            by_source=[
                {
                    "source": row["source"],
                    "record_count": int(row["record_count"]),
                    "net_amount_cents": int(row["net_amount_cents"]),
                    "net_amount_brl": cents_to_brl(int(row["net_amount_cents"])),
                    "latest_collected_at_utc": row["latest_collected_at_utc"],
                }
                for row in expense_groups
            ],
            first_collected_at_utc=expense_collected[0],
            latest_collected_at_utc=expense_collected[1],
        ),
        "contracts": _ledger(
            record_count=contract_count,
            amount_fields={
                "current_amount_cents": contract_cents,
                "current_amount_brl": cents_to_brl(contract_cents),
            },
            period_start=contract_period[0],
            period_end=contract_period[1],
            by_source=[
                {
                    "source": row["source"],
                    "record_count": int(row["record_count"]),
                    "current_amount_cents": int(row["current_amount_cents"]),
                    "latest_collected_at_utc": row["latest_collected_at_utc"],
                }
                for row in contract_groups
            ],
            first_collected_at_utc=contract_collected[0],
            latest_collected_at_utc=contract_collected[1],
        ),
        "amendments": _ledger(
            record_count=amendment_count,
            amount_fields={
                "committed_amount_cents": committed_cents,
                "committed_amount_brl": cents_to_brl(committed_cents),
                "paid_amount_cents": paid_cents,
                "paid_amount_brl": cents_to_brl(paid_cents),
            },
            period_start=str(amendment_period[0]) if amendment_period[0] is not None else None,
            period_end=str(amendment_period[1]) if amendment_period[1] is not None else None,
            by_source=[
                {
                    "source": row["source"],
                    "record_count": int(row["record_count"]),
                    "committed_amount_cents": int(row["committed_amount_cents"]),
                    "paid_amount_cents": int(row["paid_amount_cents"]),
                    "latest_collected_at_utc": row["latest_collected_at_utc"],
                }
                for row in amendment_groups
            ],
            first_collected_at_utc=amendment_collected[0],
            latest_collected_at_utc=amendment_collected[1],
        ),
        "sanctions": {
            "record_count": sanction_count,
            "by_source": [
                {
                    "source": row["source"],
                    "record_count": int(row["record_count"]),
                    "latest_collected_at_utc": row["latest_collected_at_utc"],
                }
                for row in sanction_groups
            ],
            "first_collected_at_utc": sanction_collected[0],
            "latest_collected_at_utc": sanction_collected[1],
            "note": "Sanções são contagens de registros. Não entram em soma de despesa.",
        },
        "quality": {
            "quarantined_record_count": quarantine_count,
            "expense_category_count": category_count,
        },
        "observed_sources": observed_sources,
        "catalog_source_ids_without_local_rows": catalog_without_rows,
        "limitations": limitations,
    }


def _inconclusive(
    *,
    question: str,
    intent: str,
    answer: str,
    limitations: list[str],
    evidence: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    assert_non_accusatory_language(answer)
    return 200, {
        "question_received_sanitized": question,
        "intent": intent,
        "conclusion": "ANALISE_INCONCLUSIVA",
        "answer_pt_br": answer,
        "method": "consulta_sql_deterministica",
        "model_id": None,
        "uses_language_model": False,
        "currency": "BRL",
        "amount_unit": "centavos",
        "evidence": evidence
        or {
            "row_count": 0,
            "net_amount_cents": None,
            "sources": [],
        },
        "limitations": limitations,
    }


def _verified(
    *,
    question: str,
    intent: str,
    answer: str,
    evidence: dict[str, object],
    limitations: list[str],
) -> tuple[int, dict[str, object]]:
    assert_non_accusatory_language(answer)
    return 200, {
        "question_received_sanitized": question,
        "intent": intent,
        "conclusion": "INFORMACAO_VERIFICADA",
        "answer_pt_br": answer,
        "method": "consulta_sql_deterministica",
        "model_id": None,
        "uses_language_model": False,
        "currency": "BRL",
        "amount_unit": "centavos",
        "evidence": evidence,
        "limitations": limitations,
    }


def _match_category(storage: CivicLakehouseStorage, folded_question: str) -> tuple[str | None, list[str]]:
    with storage._connect() as conn:
        categories = [
            str(row[0])
            for row in conn.execute(
                "SELECT DISTINCT expense_category FROM curated_expenses ORDER BY expense_category ASC"
            ).fetchall()
        ]
    matches = [category for category in categories if _fold(category) and _fold(category) in folded_question]
    longest = [
        category
        for category in matches
        if not any(
            _fold(category) != _fold(other) and _fold(category) in _fold(other) for other in matches
        )
    ]
    if len(longest) == 1:
        return longest[0], categories
    return None, categories


def _years_for_category(storage: CivicLakehouseStorage, category: str) -> list[int]:
    with storage._connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT competence_year
            FROM curated_expenses
            WHERE expense_category = ?
            ORDER BY competence_year ASC
            """,
            (category,),
        ).fetchall()
    return [int(row[0]) for row in rows]


def _aggregate_category(
    storage: CivicLakehouseStorage, category: str, year: int | None
) -> dict[str, object]:
    clauses = ["expense_category = ?"]
    params: list[object] = [category]
    if year is not None:
        clauses.append("competence_year = ?")
        params.append(year)
    where_sql = " AND ".join(clauses)
    with storage._connect() as conn:
        total = conn.execute(
            f"""
            SELECT COUNT(*) AS row_count, COALESCE(SUM(net_amount_cents), 0) AS net_amount_cents
            FROM curated_expenses
            WHERE {where_sql}
            """,
            tuple(params),
        ).fetchone()
        sources = conn.execute(
            f"""
            SELECT source, source_url, raw_batch_sha256, COUNT(*) AS row_count,
                   COALESCE(SUM(net_amount_cents), 0) AS net_amount_cents
            FROM curated_expenses
            WHERE {where_sql}
            GROUP BY source, source_url, raw_batch_sha256
            ORDER BY source ASC
            LIMIT 8
            """,
            tuple(params),
        ).fetchall()
    row_count = int(total[0]) if total else 0
    cents = int(total[1]) if total and row_count else 0
    return {
        "row_count": row_count,
        "net_amount_cents": cents if row_count else None,
        "net_amount_brl": cents_to_brl(cents) if row_count else None,
        "sources": [
            {
                "source": row["source"],
                "source_url": row["source_url"],
                "raw_batch_sha256": row["raw_batch_sha256"],
                "row_count": int(row["row_count"]),
                "net_amount_cents": int(row["net_amount_cents"]),
            }
            for row in sources
        ],
    }


def _detect_intent(folded: str) -> str:
    if any(token in folded for token in ("desmascar", "cpf completo", "endereco residencial")):
        return "PEDIDO_DE_DADO_PESSOAL"
    if "document" in folded or "sustenta" in folded:
        return "DOCUMENTOS_DA_DESPESA"
    if ("por que" in folded or "porque" in folded) and any(
        token in folded for token in ("sinal", "marc", "anomalia", "apont")
    ):
        return "MOTIVO_DA_SINALIZACAO"
    if any(token in folded for token in ("verific", "pendent", "faltam", "insuficient")):
        return "PENDENCIAS_PUBLICAS"
    if any(token in folded for token in ("mudou", "periodo anterior", "compar")):
        return "MUDANCA_ENTRE_PERIODOS"
    if any(token in folded for token in ("quanto", "gasto", "gast", "categoria")):
        return "GASTO_POR_CATEGORIA_E_PERIODO"
    return "NAO_RECONHECIDA"


def answer_grounded_question(
    storage: CivicLakehouseStorage, question: str
) -> tuple[int, dict[str, object]]:
    """Responde apenas com SQL sobre dados locais. Sem linha suficiente, a conclusão é inconclusiva."""
    raw = question or ""
    if len(raw) > 500:
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "A pergunta excede 500 caracteres.",
        }
    try:
        assert_non_accusatory_language(raw)
    except ValueError:
        return 422, {
            "error": "EDITORIAL_POLICY",
            "detail": "A pergunta contém linguagem vedada pela política editorial. Reformule sem juízo de culpa.",
        }

    sanitized = sanitize_untrusted_text(raw, max_length=500)
    if not sanitized.strip():
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "Informe uma pergunta sobre os dados persistidos neste ambiente.",
        }

    folded = _fold(sanitized)
    intent = _detect_intent(folded)
    base_limits = [_NOT_NATIONAL_LIMITATION, "Nenhum modelo de linguagem calculou este valor."]

    if intent == "PEDIDO_DE_DADO_PESSOAL":
        return _inconclusive(
            question=sanitized,
            intent=intent,
            answer=(
                "Identificadores pessoais completos e endereços residenciais não são divulgados. "
                "CPFs de pessoas físicas permanecem mascarados."
            ),
            limitations=base_limits,
        )

    if intent == "NAO_RECONHECIDA":
        return _inconclusive(
            question=sanitized,
            intent=intent,
            answer=(
                "Esta pergunta não corresponde a uma consulta suportada. "
                "É possível perguntar o gasto de uma categoria em um ano, a diferença entre dois anos, "
                "os documentos de um registro identificado, o motivo de uma regra identificada "
                "ou quais lacunas públicas de dados ainda existem."
            ),
            limitations=base_limits,
        )

    if intent == "PENDENCIAS_PUBLICAS":
        coverage = build_public_coverage(storage)
        with storage._connect() as conn:
            public_count = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*) FROM audit_dossiers
                    WHERE status IN ({",".join("?" for _ in _PUBLIC_DOSSIER_STATUSES)})
                    """,
                    _PUBLIC_DOSSIER_STATUSES,
                ).fetchone()[0]
            )
        missing = coverage["catalog_source_ids_without_local_rows"]
        answer = (
            f"Há {public_count} dossiê(s) em estado público revisado neste ambiente. "
            f"Fontes do catálogo sem linhas locais: {', '.join(missing) if missing else 'nenhuma'}."
            " Registros em revisão interna não são listados nesta resposta."
        )
        return _verified(
            question=sanitized,
            intent=intent,
            answer=answer,
            evidence={
                "published_dossier_count": public_count,
                "catalog_source_ids_without_local_rows": missing,
                "quarantined_record_count": coverage["quality"]["quarantined_record_count"],
                "internal_triage_disclosed": False,
            },
            limitations=[
                *base_limits,
                "A contagem de dossiês em triagem interna não é pública.",
            ],
        )

    if intent == "MOTIVO_DA_SINALIZACAO":
        rule_match = _RULE_RE.search(sanitized.upper())
        if rule_match is None:
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer=(
                    "Uma sinalização só existe quando uma regra determinística registra um sinal "
                    "e, quando o caso é nominal e sensível, permanece em revisão humana antes de publicação. "
                    "Esta pergunta não identificou o código da regra nem o registro. A conclusão é inconclusiva."
                ),
                limitations=base_limits,
            )
        rule_code = rule_match.group(0)
        with storage._connect() as conn:
            public_rows = conn.execute(
                f"""
                SELECT dossier_id, rule_code, status
                FROM audit_dossiers
                WHERE rule_code = ?
                  AND status IN ({",".join("?" for _ in _PUBLIC_DOSSIER_STATUSES)})
                ORDER BY dossier_id ASC
                LIMIT 5
                """,
                (rule_code, *_PUBLIC_DOSSIER_STATUSES),
            ).fetchall()
        if not public_rows:
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer=(
                    f"Não há dossiê público revisado para a regra {rule_code} neste ambiente. "
                    "Sem esse registro, não há motivo publicável para uma sinalização específica."
                ),
                limitations=[*base_limits, "Dossiês em triagem interna não são descritos nesta resposta."],
            )
        ids = ", ".join(str(row["dossier_id"]) for row in public_rows)
        return _verified(
            question=sanitized,
            intent=intent,
            answer=(
                f"A regra {rule_code} possui dossiê público revisado neste ambiente: {ids}. "
                "O motivo verificável é a execução dessa regra sobre os hashes de proveniência do dossiê, "
                "não um juízo sobre pessoas."
            ),
            evidence={
                "rule_code": rule_code,
                "public_dossier_ids": [str(row["dossier_id"]) for row in public_rows],
            },
            limitations=base_limits,
        )

    if intent == "DOCUMENTOS_DA_DESPESA":
        tokens = _HEX64_RE.findall(sanitized) + _DOC_RE.findall(sanitized)
        quoted = re.findall(r'"([^"]{1,80})"', sanitized)
        tokens.extend(quoted)
        if not tokens:
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer="Informe o número do documento ou a chave do registro para localizar a fonte.",
                limitations=base_limits,
            )
        found: list[dict[str, object]] = []
        with storage._connect() as conn:
            for token in tokens[:5]:
                rows = conn.execute(
                    """
                    SELECT natural_key, document_number, source, source_url, source_record_id,
                           document_evidence_url, raw_batch_sha256, net_amount_cents, expense_category
                    FROM curated_expenses
                    WHERE natural_key = ? OR document_number = ? OR source_record_id = ?
                    LIMIT 5
                    """,
                    (token, token, token),
                ).fetchall()
                found.extend(dict(row) for row in rows)
        if not found:
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer="Nenhum documento local corresponde ao identificador informado.",
                limitations=base_limits,
            )
        first = found[0]
        return _verified(
            question=sanitized,
            intent=intent,
            answer=(
                f"O registro local {first['document_number']} da categoria {first['expense_category']} "
                f"está ligado à fonte {first['source']} e ao lote {first['raw_batch_sha256']}."
            ),
            evidence={"documents": found[:5]},
            limitations=base_limits,
        )

    category, available = _match_category(storage, folded)
    years = [int(year) for year in _YEAR_RE.findall(sanitized)]
    if category is None:
        sample = ", ".join(available[:8]) if available else "nenhuma categoria persistida"
        return _inconclusive(
            question=sanitized,
            intent=intent,
            answer=(
                "Não foi possível identificar uma única categoria persistida na pergunta. "
                f"Categorias locais disponíveis: {sample}."
            ),
            limitations=base_limits,
        )

    if intent == "MUDANCA_ENTRE_PERIODOS":
        if len(years) >= 2:
            year_a, year_b = years[0], years[1]
        elif len(years) == 1:
            year_a, year_b = years[0] - 1, years[0]
        else:
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer="Informe o ano para comparar a categoria com o período anterior.",
                limitations=base_limits,
            )
        left = _aggregate_category(storage, category, year_a)
        right = _aggregate_category(storage, category, year_b)
        if not left["row_count"] or not right["row_count"]:
            present = _years_for_category(storage, category)
            return _inconclusive(
                question=sanitized,
                intent=intent,
                answer=(
                    f"Não há registros locais suficientes de {category} em {year_a} e {year_b} "
                    f"para comparar os períodos. Anos com linhas desta categoria: {present or 'nenhum'}."
                ),
                limitations=base_limits,
                evidence={"year_a": left, "year_b": right},
            )
        difference = int(right["net_amount_cents"]) - int(left["net_amount_cents"])
        return _verified(
            question=sanitized,
            intent=intent,
            answer=(
                f"Na categoria {category}, os registros locais somam {left['net_amount_brl']} BRL em {year_a} "
                f"e {right['net_amount_brl']} BRL em {year_b}. "
                f"A diferença aritmética dos totais locais é {cents_to_brl(difference)} BRL."
            ),
            evidence={
                "category": category,
                "year_a": left,
                "year_b": right,
                "difference_cents": difference,
                "difference_brl": cents_to_brl(difference),
            },
            limitations=[
                *base_limits,
                "A diferença é aritmética entre somas locais. Não indica irregularidade.",
            ],
        )

    year = years[0] if len(years) == 1 else None
    if len(years) > 1:
        return _inconclusive(
            question=sanitized,
            intent=intent,
            answer="A pergunta cita mais de um ano. Informe um único ano ou peça a comparação entre períodos.",
            limitations=base_limits,
        )
    aggregate = _aggregate_category(storage, category, year)
    if not aggregate["row_count"]:
        present = _years_for_category(storage, category)
        period = f" em {year}" if year is not None else ""
        return _inconclusive(
            question=sanitized,
            intent=intent,
            answer=(
                f"Não há registros locais da categoria {category}{period}. "
                f"Anos com linhas desta categoria: {present or 'nenhum'}."
            ),
            limitations=base_limits,
            evidence=aggregate,
        )
    period_label = f"em {year}" if year is not None else "em todos os anos persistidos"
    return _verified(
        question=sanitized,
        intent=intent,
        answer=(
            f"Os registros locais da categoria {category} {period_label} somam "
            f"{aggregate['net_amount_brl']} BRL em {aggregate['row_count']} linha(s)."
        ),
        evidence={"category": category, "year": year, **aggregate},
        limitations=base_limits,
    )

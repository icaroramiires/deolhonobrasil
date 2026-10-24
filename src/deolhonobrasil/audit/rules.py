"""Regras determinísticas de auditoria e geração de sinais de integridade cívica.

Implementa as regras da Fase 4:
- AuditSignal: estrutura imutável de sinal com 3 camadas epistêmicas e verificação anti-acusatória.
- R-PNCP-OVERPRICE-Z3: detecção de desvio paramétrico em valores unitários ou totais de contratos.
- R-CGU-HHI-CONCENTRATION: detecção de concentração excessiva de mercado em fornecedores de órgãos.
- R-CEAP-OUTLIER-Z3: detecção de despesas de cota parlamentar atípicas frente ao subgrupo comparável.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from deolhonobrasil.audit.statistics import (
    calculate_hhi_concentration,
    calculate_z_score,
    evaluate_benford_first_digit,
)
from deolhonobrasil.pipeline.models import (
    CuratedParliamentaryAmendment,
    CuratedPublicContract,
    CuratedPublicExpense,
    CuratedSanctionRecord,
    EpistemicClassification,
    assert_non_accusatory_language,
)
from deolhonobrasil.pipeline.privacy import compute_sha256_text, sanitize_untrusted_text


@dataclass(frozen=True, slots=True)
class AuditSignal:
    """Sinal determinístico emitido por regra de auditoria cívica com proveniência e restrições epistêmicas."""

    signal_id: str
    rule_code: str
    title: str
    official_fact_summary: str
    statistical_inference_summary: str
    scope_limitation_summary: str
    epistemic_layer: EpistemicClassification
    metric_name: str
    metric_value: Decimal
    threshold_value: Decimal
    audited_amount: Decimal
    provenance_hashes: tuple[str, ...]
    requires_human_review: bool

    def __post_init__(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("signal_id é obrigatório.")
        if not self.rule_code.strip():
            raise ValueError("rule_code é obrigatório.")

        # Conversão defensiva caso uma lista ou iterável tenha sido fornecido para provenance_hashes
        if not isinstance(self.provenance_hashes, tuple):
            object.__setattr__(self, "provenance_hashes", tuple(self.provenance_hashes))

        # Validação estrita da Política Editorial (Seção 12.1): nenhuma linguagem acusatória permitida
        assert_non_accusatory_language(self.title)
        assert_non_accusatory_language(self.official_fact_summary)
        assert_non_accusatory_language(self.statistical_inference_summary)
        assert_non_accusatory_language(self.scope_limitation_summary)


def evaluate_contract_overpricing_rule(
    contract: CuratedPublicContract,
    peer_unit_prices: Sequence[Decimal],
    z_threshold: Decimal = Decimal("3.00"),
) -> AuditSignal | None:
    """Avalia se o valor do contrato apresenta dispersão estatística atípica (Z >= z_threshold).

    Código da Regra: R-PNCP-OVERPRICE-Z3
    """
    if len(peer_unit_prices) < 2:
        return None

    try:
        z_score = calculate_z_score(contract.current_amount, peer_unit_prices)
    except ValueError:
        return None

    if z_score < z_threshold:
        return None

    clean_organ = sanitize_untrusted_text(contract.organ_name, 120)
    clean_supplier = sanitize_untrusted_text(contract.supplier_name, 120)
    clean_control = sanitize_untrusted_text(contract.pncp_control_number, 50)
    contract_date_str = contract.signature_date.isoformat()

    title = f"Divergência estatística de valor em contrato PNCP {clean_control}"
    fact_summary = (
        f"Contrato firmado por {clean_organ} com o fornecedor {clean_supplier} no montante "
        f"de R$ {contract.current_amount:.2f} em {contract_date_str} (Controle PNCP: {clean_control})."
    )
    stat_summary = (
        f"O valor analisado apresenta Z-score amostral de {z_score}, superando o limiar paramétrico "
        f"definido de {z_threshold} em relação à distribuição dos contratos de referência da mesma categoria."
    )
    scope_limit = (
        "A divergência estatística apurada representa um indicador quantitativo de dispersão de preços e "
        "não constitui comprovação de sobrepreço nem de irregularidade na contratação. Variações legítimas "
        "podem decorrer de especificidades técnicas, garantias estendidas, flutuações de mercado ou logística."
    )

    provenance_hashes = (contract.provenance.raw_batch_sha256, contract.natural_key)

    return AuditSignal(
        signal_id=f"SIG-PNCP-{clean_control[:24]}-{contract.provenance.raw_batch_sha256[:8]}",
        rule_code="R-PNCP-OVERPRICE-Z3",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
        metric_name="z_score",
        metric_value=z_score,
        threshold_value=z_threshold,
        audited_amount=contract.current_amount,
        provenance_hashes=provenance_hashes,
        requires_human_review=True,
    )


def evaluate_supplier_concentration_rule(
    organ_code: str,
    organ_name: str,
    expenses: Sequence[CuratedPublicExpense],
    hhi_threshold: Decimal = Decimal("2500.00"),
) -> AuditSignal | None:
    """Avalia se os gastos de um órgão apresentam concentração excessiva de fornecedores via índice HHI.

    Código da Regra: R-CGU-HHI-CONCENTRATION
    """
    clean_organ_code = sanitize_untrusted_text(organ_code, 50)
    clean_organ_name = sanitize_untrusted_text(organ_name, 150)

    # Filtrar despesas pertencentes ao órgão, ou usar todas se organ_code coincidir
    relevant = [e for e in expenses if not clean_organ_code or e.organ_code == clean_organ_code]
    if not relevant:
        return None

    supplier_totals: dict[str, Decimal] = defaultdict(Decimal)
    for exp in relevant:
        sup_key = exp.supplier_doc_normalized or exp.supplier_name
        supplier_totals[sup_key] += exp.net_amount

    total_amount = sum(supplier_totals.values())
    if total_amount <= Decimal("0.00"):
        return None

    shares_by_supplier = {sup: amt / total_amount for sup, amt in supplier_totals.items()}
    hhi_score, classification = calculate_hhi_concentration(shares_by_supplier)

    if hhi_score < hhi_threshold:
        return None

    title = f"Concentração elevada de fornecedores no órgão {clean_organ_name}"
    fact_summary = (
        f"O órgão público {clean_organ_name} (código: {clean_organ_code}) executou R$ {total_amount:.2f} "
        f"distribuídos entre {len(supplier_totals)} fornecedores no período analisado."
    )
    stat_summary = (
        f"O Índice Herfindahl-Hirschman (HHI) apurado foi de {hhi_score}, atingindo a classificação "
        f"'{classification}' e ultrapassando o limiar de atenção de {hhi_threshold} pontos."
    )
    scope_limit = (
        "Elevada concentração de contratações pode ser decorrente de especialização técnica exclusiva, "
        "concessionárias de serviços públicos essenciais ou escassez de mercado regional, demandando análise "
        "contextual antes de qualquer conclusão sobre competitividade do certame."
    )

    provenance_list = sorted({e.provenance.raw_batch_sha256 for e in relevant})
    sig_seed = f"{clean_organ_code}|{hhi_score}|{total_amount}"
    sig_hash = compute_sha256_text(sig_seed)[:8]

    return AuditSignal(
        signal_id=f"SIG-HHI-{clean_organ_code[:20]}-{sig_hash}",
        rule_code="R-CGU-HHI-CONCENTRATION",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
        metric_name="hhi_index",
        metric_value=hhi_score,
        threshold_value=hhi_threshold,
        audited_amount=total_amount,
        provenance_hashes=tuple(provenance_list),
        requires_human_review=True,
    )


def evaluate_ceap_quota_outlier_rule(
    expense: CuratedPublicExpense,
    peer_expenses: Sequence[Decimal],
    z_threshold: Decimal = Decimal("3.00"),
) -> AuditSignal | None:
    """Avalia se um reembolso de cota parlamentar (CEAP/CEAPS) diverge significativamente do grupo de pares.

    Código da Regra: R-CEAP-OUTLIER-Z3
    """
    if len(peer_expenses) < 2:
        return None

    try:
        z_score = calculate_z_score(expense.net_amount, peer_expenses)
    except ValueError:
        return None

    if z_score < z_threshold:
        return None

    agent_name = sanitize_untrusted_text(expense.public_agent_name, 100)
    category = sanitize_untrusted_text(expense.expense_category, 100)
    issue_date_str = expense.issue_date.isoformat()

    title = f"Discrepância estatística em cota parlamentar de {agent_name}"
    fact_summary = (
        f"Reembolso de cota registrado em nome de {agent_name} na subcota '{category}' "
        f"no valor de R$ {expense.net_amount:.2f} com data de emissão em {issue_date_str} "
        f"(Documento: {expense.document_number})."
    )
    stat_summary = (
        f"O valor reembolsado possui Z-score amostral de {z_score}, situando-se além do parâmetro "
        f"crítico de {z_threshold} em relação aos lançamentos equivalentes na mesma rubrica orçamentária."
    )
    scope_limit = (
        "A identificação de valor atípico aponta desvio em relação ao comportamento mediano de despesas correlatas, "
        "não constituindo indicativo de ilicitude. Despesas de deslocamento urgente, comitivas ou períodos legislativos "
        "específicos podem justificar variações pontuais devidamente atestadas pela administração."
    )

    provenance_hashes = (expense.provenance.raw_batch_sha256, expense.natural_key)

    return AuditSignal(
        signal_id=f"SIG-CEAP-{expense.natural_key[:16]}",
        rule_code="R-CEAP-OUTLIER-Z3",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
        metric_name="z_score",
        metric_value=z_score,
        threshold_value=z_threshold,
        audited_amount=expense.net_amount,
        provenance_hashes=provenance_hashes,
        requires_human_review=True,
    )


def evaluate_ceis_cnep_sanctioned_supplier_rule(
    record: CuratedPublicContract | CuratedPublicExpense,
    sanctions: Sequence[CuratedSanctionRecord],
) -> AuditSignal | None:
    """Cruza contrato ou despesa contra sanções CEIS/CNEP vigentes (`SPEC-0007` / `FR-017` / `NFR-010`).

    Código da Regra: R-CROSS-CEIS-SANCTIONED-SUPPLIER
    """
    # NFR-010: Jamais realizar cruzamento automático por CPF mascarado para evitar homonímia.
    if record.supplier_doc_type != "CNPJ":
        return None

    act_date = (
        record.signature_date
        if isinstance(record, CuratedPublicContract)
        else record.issue_date
    )
    audited_amount = (
        record.current_amount
        if isinstance(record, CuratedPublicContract)
        else record.net_amount
    )

    matched_sanction: CuratedSanctionRecord | None = None
    for s in sanctions:
        if s.sanctioned_doc_type != "CNPJ":
            continue
        if s.sanctioned_doc_normalized != record.supplier_doc_normalized:
            continue
        if act_date < s.start_date:
            continue
        if s.end_date is not None and act_date > s.end_date:
            continue
        matched_sanction = s
        break

    if matched_sanction is None:
        return None

    clean_supplier = sanitize_untrusted_text(record.supplier_name, 120)
    clean_organ = sanitize_untrusted_text(record.organ_name, 120)
    clean_sanc_type = sanitize_untrusted_text(matched_sanction.sanction_type, 120)
    clean_sanc_organ = sanitize_untrusted_text(matched_sanction.sanctioning_organ, 120)

    title = (
        f"Divergência cadastral entre registro de pagamento/contrato e apontamento CEIS/CNEP "
        f"para {clean_supplier}"
    )
    fact_summary = (
        f"Registro de vínculo financeiro no órgão {clean_organ} em {act_date.isoformat()} "
        f"no valor de R$ {audited_amount:.2f} com CNPJ {record.supplier_doc_normalized}, "
        f"concomitante ao registro CEIS/CNEP '{matched_sanction.sanction_code}' ({clean_sanc_type}, "
        f"órgão sancionador: {clean_sanc_organ}, vigência desde {matched_sanction.start_date.isoformat()})."
    )
    stat_summary = (
        "Cruzamento determinístico exato por CNPJ de 14 dígitos e interseção temporal no intervalo "
        "de vigência da restrição administrativa."
    )
    scope_limit = (
        "A coexistência de registro no CEIS/CNEP e execução contratual não comprova irregularidade automática. "
        "Restrições administrativas podem ter escopo limitado exclusivamente à esfera ou órgão sancionador "
        "(art. 156, III da Lei 14.133/2021), estar amparadas por decisão judicial liminar suspensiva ou "
        "referir-se a contrato assinado anteriormente à sanção para serviços contínuos essenciais."
    )

    provenance_hashes = (
        record.provenance.raw_batch_sha256,
        matched_sanction.provenance.raw_batch_sha256,
    )
    sig_hash = compute_sha256_text(
        f"{record.natural_key}|{matched_sanction.natural_key}"
    )[:12]

    return AuditSignal(
        signal_id=f"SIG-CEIS-{sig_hash}",
        rule_code="R-CROSS-CEIS-SANCTIONED-SUPPLIER",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
        metric_name="active_sanction_overlap",
        metric_value=Decimal("1.00"),
        threshold_value=Decimal("1.00"),
        audited_amount=audited_amount,
        provenance_hashes=provenance_hashes,
        requires_human_review=True,
    )


def evaluate_amendment_execution_divergence_rule(
    amendment: CuratedParliamentaryAmendment,
) -> AuditSignal | None:
    """Verifica divergência contábil onde o valor pago supera o valor empenhado na emenda (`SPEC-0007`).

    Código da Regra: R-CROSS-AMENDMENT-EXECUTION-GAP
    """
    if amendment.paid_amount <= amendment.committed_amount:
        return None

    gap = (amendment.paid_amount - amendment.committed_amount).quantize(Decimal("0.01"))
    clean_code = sanitize_untrusted_text(amendment.amendment_code, 50)
    clean_author = sanitize_untrusted_text(amendment.author_name, 120)

    title = f"Divergência contábil entre valor pago e empenhado na emenda {clean_code}"
    fact_summary = (
        f"A emenda parlamentar {clean_code} ({amendment.year}, autor: {clean_author}) registra "
        f"valor empenhado de R$ {amendment.committed_amount:.2f} e valor pago de R$ {amendment.paid_amount:.2f}."
    )
    stat_summary = (
        f"Diferença positiva de R$ {gap:.2f} entre o montante pago e o empenhado do exercício corrente."
    )
    scope_limit = (
        "Divergências entre valores pagos e empenhados no mesmo recorte temporal frequentemente decorrem "
        "da liquidação de Restos a Pagar (RAP) de exercícios anteriores ou de consolidação assíncrona "
        "entre SIAFI e Portal da Transparência, exigindo verificação das notas de empenho vinculadas."
    )

    return AuditSignal(
        signal_id=f"SIG-AMD-GAP-{clean_code}-{amendment.natural_key[:8]}",
        rule_code="R-CROSS-AMENDMENT-EXECUTION-GAP",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
        metric_name="paid_minus_committed_brl",
        metric_value=gap,
        threshold_value=Decimal("0.00"),
        audited_amount=amendment.paid_amount,
        provenance_hashes=(amendment.provenance.raw_batch_sha256, amendment.natural_key),
        requires_human_review=True,
    )


def evaluate_benford_distribution_rule(
    expenses: Sequence[CuratedPublicExpense],
    context_label: str = "Conjunto de Despesas",
    min_sample_size: int = 50,
    mad_threshold: Decimal = Decimal("0.01500"),
) -> AuditSignal | None:
    """Avalia se a distribuição de primeiro dígito de despesas públicas desvia da Lei de Benford (`SPEC-0008`).

    Código da Regra: R-STAT-BENFORD-DEVIATION
    Critério: Amostra com ao menos min_sample_size despesas estritamente positivas e MAD > mad_threshold (Não Conforme).
    """
    positive_expenses = [e for e in expenses if e.net_amount > Decimal("0")]
    if len(positive_expenses) < min_sample_size:
        return None

    amounts = [e.net_amount for e in positive_expenses]
    try:
        benford_res = evaluate_benford_first_digit(amounts)
    except ValueError:
        return None

    mad = Decimal(str(benford_res["mad"]))
    if mad <= mad_threshold:
        return None

    chi_sq = Decimal(str(benford_res["chi_square"]))
    clean_context = sanitize_untrusted_text(context_label, 100)
    total_audited = sum(amounts)
    unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in positive_expenses}))

    title = f"Desvio estatístico de primeiro dígito frente à Lei de Benford em {clean_context}"
    fact_summary = (
        f"Foram avaliadas {len(positive_expenses)} despesas públicas totalizando R$ {total_audited:.2f} "
        f"no contexto {clean_context}."
    )
    stat_summary = (
        f"O Desvio Médio Absoluto (MAD) do primeiro dígito foi de {mad} (Qui-Quadrado: {chi_sq}), "
        f"superando o limiar de conformidade de {mad_threshold}."
    )
    scope_limit = (
        "O desvio em relação à Lei de Benford aponta atipicidade na distribuição de dígitos, mas não comprova "
        "irregularidade nem má-fé. Certas categorias de compras públicas possuem tabelas fixas, tarifas reguladas "
        "ou tetos orçamentários que naturalmente concentram determinados valores."
    )

    return AuditSignal(
        signal_id=f"SIG-BENFORD-{compute_sha256_text(f'{clean_context}:{mad}:{len(positive_expenses)}')[:16]}",
        rule_code="R-STAT-BENFORD-DEVIATION",
        title=title,
        official_fact_summary=fact_summary,
        statistical_inference_summary=stat_summary,
        scope_limitation_summary=scope_limit,
        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
        metric_name="benford_first_digit_mad",
        metric_value=mad,
        threshold_value=mad_threshold,
        audited_amount=total_audited,
        provenance_hashes=unique_hashes,
        requires_human_review=True,
    )


def evaluate_split_expense_rule(
    expenses: Sequence[CuratedPublicExpense],
    single_limit_threshold: Decimal = Decimal("50000.00"),
    aggregate_threshold: Decimal = Decimal("100000.00"),
    window_days: int = 90,
    min_count: int = 3,
) -> list[AuditSignal]:
    """Identifica concentrações de despesas sucessivas para o mesmo fornecedor e órgão em janela móvel (`SPEC-0008`).

    Código da Regra: R-SPLIT-EXPENSE-THRESHOLD
    Critério: Transações com o mesmo órgão e fornecedor (CNPJ), cada uma <= single_limit_threshold,
    acumulando total >= aggregate_threshold em um intervalo <= window_days com ao menos min_count compras.
    """
    groups: dict[tuple[str, str, str, str], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if (
            exp.net_amount > Decimal("0")
            and exp.net_amount <= single_limit_threshold
            and exp.issue_date is not None
            and exp.supplier_doc_normalized
        ):
            group_key = (
                exp.organ_code,
                exp.organ_name,
                exp.supplier_doc_normalized,
                exp.supplier_name,
            )
            groups[group_key].append(exp)

    signals: list[AuditSignal] = []

    for (organ_code, organ_name, supplier_doc, supplier_name), items in groups.items():
        if len(items) < min_count:
            continue

        sorted_items = sorted(items, key=lambda x: x.issue_date)
        i = 0
        n = len(sorted_items)
        while i < n:
            start_exp = sorted_items[i]
            window_items: list[CuratedPublicExpense] = []
            for j in range(i, n):
                diff_days = (sorted_items[j].issue_date - start_exp.issue_date).days
                if diff_days <= window_days:
                    window_items.append(sorted_items[j])
                else:
                    break

            if len(window_items) >= min_count:
                window_total = sum(x.net_amount for x in window_items)
                if window_total >= aggregate_threshold:
                    clean_organ = sanitize_untrusted_text(organ_name, 80)
                    clean_supplier = sanitize_untrusted_text(supplier_name, 80)
                    clean_doc = sanitize_untrusted_text(supplier_doc, 20)
                    start_date_str = window_items[0].issue_date.isoformat()
                    end_date_str = window_items[-1].issue_date.isoformat()
                    elapsed_days = (window_items[-1].issue_date - window_items[0].issue_date).days
                    unique_hashes = tuple(sorted({x.provenance.raw_batch_sha256 for x in window_items}))

                    title = f"Concentração de transações sequenciais próximas ao limiar de dispensa para {clean_supplier}"
                    fact_summary = (
                        f"Foram registradas {len(window_items)} despesas pelo órgão {clean_organ} "
                        f"para o fornecedor {clean_supplier} ({clean_doc}) entre {start_date_str} e {end_date_str}, "
                        f"com valores unitários inferiores a R$ {single_limit_threshold:.2f}."
                    )
                    stat_summary = (
                        f"O somatório acumulado no intervalo de {elapsed_days} dias alcançou R$ {window_total:.2f}, "
                        f"superando o patamar de referência de R$ {aggregate_threshold:.2f}."
                    )
                    scope_limit = (
                        "A ocorrência de pagamentos parcelados para o mesmo fornecedor em curto intervalo requer "
                        "verificação da natureza dos objetos contratados. Não há constatação de irregularidade quando as "
                        "aquisições correspondem a objetos de naturezas distintas, compras emergenciais ou contratos continuados autorizados em lei."
                    )

                    sig_id = f"SIG-SPLIT-{compute_sha256_text(f'{organ_code}:{supplier_doc}:{start_date_str}:{len(window_items)}')[:16]}"
                    signals.append(
                        AuditSignal(
                            signal_id=sig_id,
                            rule_code="R-SPLIT-EXPENSE-THRESHOLD",
                            title=title,
                            official_fact_summary=fact_summary,
                            statistical_inference_summary=stat_summary,
                            scope_limitation_summary=scope_limit,
                            epistemic_layer=EpistemicClassification.UNVALIDATED_HYPOTHESIS,
                            metric_name="split_cumulative_amount",
                            metric_value=window_total,
                            threshold_value=aggregate_threshold,
                            audited_amount=window_total,
                            provenance_hashes=unique_hashes,
                            requires_human_review=True,
                        )
                    )
                    i += len(window_items)
                    continue

            i += 1

    return signals



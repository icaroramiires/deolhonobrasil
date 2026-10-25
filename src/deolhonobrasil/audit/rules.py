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
from datetime import date, timedelta
from decimal import Decimal

from deolhonobrasil.audit.statistics import (
    calculate_hhi_concentration,
    calculate_z_score,
    evaluate_benford_first_digit,
)
from deolhonobrasil.pipeline.models import (
    CuratedCompanyRegistrationRecord,
    CuratedCorporateMemberRecord,
    CuratedElectoralDonation,
    CuratedParliamentaryAmendment,
    CuratedPublicAgentRecord,
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


def extract_cnpj_root(raw_doc: str) -> str | None:
    """Extrai a raiz societária de 8 dígitos de um CNPJ válido de 14 dígitos (`SPEC-0009`).

    Rejeita categoricamente CPFs mascarados (`***.XXX.XXX-**`) e strings que não contenham
    exatamente 14 dígitos (`NFR-012`).
    """
    digits = "".join(ch for ch in str(raw_doc) if ch.isdigit())
    if len(digits) != 14:
        return None
    return digits[:8]


def evaluate_shared_cnpj_root_rule(
    expenses: Sequence[CuratedPublicExpense],
    min_branches: int = 2,
    min_aggregate_amount: Decimal = Decimal("100000.00"),
) -> list[AuditSignal]:
    """Identifica despesas distribuídas entre filiais do mesmo grupo societário (mesma raiz CNPJ) no mesmo órgão (`SPEC-0009`).

    Código da Regra: R-SHARED-CNPJ-ROOT
    """
    groups: dict[tuple[str, str, str], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.net_amount <= Decimal("0"):
            continue
        root = extract_cnpj_root(exp.supplier_doc_normalized)
        if root is not None:
            groups[(exp.organ_code, exp.organ_name, root)].append(exp)

    signals: list[AuditSignal] = []

    for (organ_code, organ_name, root_cnpj), items in groups.items():
        distinct_branches = {e.supplier_doc_normalized for e in items}
        if len(distinct_branches) < min_branches:
            continue

        total_amount = sum(e.net_amount for e in items)
        if total_amount < min_aggregate_amount:
            continue

        clean_organ = sanitize_untrusted_text(organ_name, 100)
        unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in items}))

        title = f"Despesas distribuídas entre múltiplas filiais do grupo econômico com raiz {root_cnpj}"
        fact_summary = (
            f"Foram registradas despesas para {len(distinct_branches)} filiais com raiz {root_cnpj} "
            f"no órgão {clean_organ}, totalizando R$ {total_amount:.2f}."
        )
        stat_summary = (
            f"Concentração de {len(distinct_branches)} filiais distintas do mesmo grupo societário no órgão, "
            f"somando R$ {total_amount:.2f} (limiar: R$ {min_aggregate_amount:.2f})."
        )
        scope_limit = (
            "Empresas pertencentes ao mesmo grupo econômico (matriz e filiais) possuem autorização jurídica para "
            "atuar com inscrições individualizadas. A contratação concomitante de filiais pode decorrer de "
            "unidades operacionais em municípios distintos ou fornecimento de itens de lotes separados."
        )

        sig_id = f"SIG-ROOT-{compute_sha256_text(f'{organ_code}:{root_cnpj}:{len(items)}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-SHARED-CNPJ-ROOT",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                metric_name="distinct_branches_count",
                metric_value=Decimal(str(len(distinct_branches))),
                threshold_value=min_aggregate_amount,
                audited_amount=total_amount,
                provenance_hashes=unique_hashes,
                requires_human_review=True,
            )
        )

    return signals


def evaluate_monopolistic_supplier_category_rule(
    expenses: Sequence[CuratedPublicExpense],
    dominance_share_threshold: Decimal = Decimal("0.80"),
    min_total_amount: Decimal = Decimal("100000.00"),
    min_transactions: int = 3,
) -> list[AuditSignal]:
    """Identifica concentração monopolística (>= 80%) de um grupo/fornecedor em categoria/órgão (`SPEC-0009`).

    Código da Regra: R-PROCUREMENT-MONOPOLISTIC-SUPPLIER
    """
    cat_groups: dict[tuple[str, str, str], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.net_amount > Decimal("0") and exp.expense_category:
            cat_groups[(exp.organ_code, exp.organ_name, exp.expense_category)].append(exp)

    signals: list[AuditSignal] = []

    for (organ_code, organ_name, category), items in cat_groups.items():
        if len(items) < min_transactions:
            continue

        total_cat_amount = sum(e.net_amount for e in items)
        if total_cat_amount < min_total_amount:
            continue

        # Agrupa gastos por raiz de CNPJ (se existir) ou pelo doc_normalized
        supplier_subgroups: dict[str, list[CuratedPublicExpense]] = defaultdict(list)
        for e in items:
            root = extract_cnpj_root(e.supplier_doc_normalized) or e.supplier_doc_normalized
            supplier_subgroups[root].append(e)

        for root_key, sup_items in supplier_subgroups.items():
            sup_amount = sum(e.net_amount for e in sup_items)
            share = sup_amount / total_cat_amount

            if share >= dominance_share_threshold:
                clean_organ = sanitize_untrusted_text(organ_name, 100)
                clean_cat = sanitize_untrusted_text(category, 80)
                dominant_name = sanitize_untrusted_text(sup_items[0].supplier_name, 80)
                unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in sup_items}))
                share_pct = (share * Decimal("100")).quantize(Decimal("0.01"))
                thresh_pct = (dominance_share_threshold * Decimal("100")).quantize(Decimal("0.01"))

                title = f"Concentração elevada de gastos com único fornecedor na categoria {clean_cat}"
                fact_summary = (
                    f"O fornecedor {dominant_name} respondeu por R$ {sup_amount:.2f} do total de "
                    f"R$ {total_cat_amount:.2f} na categoria {clean_cat} no órgão {clean_organ}."
                )
                stat_summary = (
                    f"Participação de {share_pct}% dos dispêndios da categoria concentrada no mesmo grupo "
                    f"(limiar: {thresh_pct}%)."
                )
                scope_limit = (
                    "A concentração em um único fornecedor pode decorrer de especialização técnica exclusiva, "
                    "direitos autorais protegidos ou fornecimento em localidade sem outros concorrentes viáveis, "
                    "não caracterizando irregularidade automática."
                )

                sig_id = f"SIG-MONOP-{compute_sha256_text(f'{organ_code}:{category}:{root_key}')[:16]}"
                signals.append(
                    AuditSignal(
                        signal_id=sig_id,
                        rule_code="R-PROCUREMENT-MONOPOLISTIC-SUPPLIER",
                        title=title,
                        official_fact_summary=fact_summary,
                        statistical_inference_summary=stat_summary,
                        scope_limitation_summary=scope_limit,
                        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                        metric_name="supplier_category_share",
                        metric_value=share.quantize(Decimal("0.01")),
                        threshold_value=dominance_share_threshold,
                        audited_amount=sup_amount,
                        provenance_hashes=unique_hashes,
                        requires_human_review=True,
                    )
                )

    return signals


_GENERIC_DOC_NUMBERS: frozenset[str] = frozenset({
    "",
    "S/N",
    "SN",
    "0",
    "-",
    "--",
    "SEM NUMERO",
    "SEM NÚMERO",
    "NAO INFORMADO",
    "NÃO INFORMADO",
})

_PHYSICAL_PRESENCE_KEYWORDS: tuple[str, ...] = (
    "COMBUSTIVEL",
    "COMBUSTÍVEL",
    "ALIMENTACAO",
    "ALIMENTAÇÃO",
    "HOSPEDAGEM",
    "HOTEL",
    "LOCACAO DE VEICULO",
    "LOCAÇÃO DE VEÍCULO",
    "LOCACAO DE VEICULOS",
    "LOCAÇÃO DE VEÍCULOS",
    "TAXI",
    "TÁXI",
    "REFEICAO",
    "REFEIÇÃO",
    "ABASTECIMENTO",
)


def evaluate_duplicate_expense_document_rule(
    expenses: Sequence[CuratedPublicExpense],
) -> list[AuditSignal]:
    """Identifica reembolsos em duplicidade do mesmo documento fiscal para o mesmo fornecedor (`SPEC-0010`).

    Código da Regra: R-DUPLICATE-EXPENSE-DOCUMENT
    """
    groups: dict[tuple[str, str], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.net_amount <= Decimal("0"):
            continue
        clean_doc = exp.document_number.strip().upper()
        if clean_doc in _GENERIC_DOC_NUMBERS or len(clean_doc) < 2:
            continue
        if not exp.supplier_doc_normalized:
            continue
        groups[(exp.supplier_doc_normalized, clean_doc)].append(exp)

    signals: list[AuditSignal] = []

    for (supplier_doc, doc_number), items in groups.items():
        if len(items) < 2:
            continue

        total_amount = sum(e.net_amount for e in items)
        clean_supplier = sanitize_untrusted_text(items[0].supplier_name, 80)
        clean_doc_num = sanitize_untrusted_text(doc_number, 50)
        unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in items}))

        title = f"Reembolso de documento fiscal em duplicidade para {clean_supplier}"
        fact_summary = (
            f"Foram registradas {len(items)} despesas com o mesmo documento {clean_doc_num} "
            f"do fornecedor {clean_supplier} ({supplier_doc}), totalizando R$ {total_amount:.2f}."
        )
        stat_summary = (
            f"Identificadas {len(items)} ocorrências idênticas de comprovação fiscal para o "
            f"mesmo favorecido na base pública."
        )
        scope_limit = (
            "Documentos com mesma numeração podem decorrer de séries fiscais distintas não informadas "
            "no cadastro, reemissão com estorno contábil registrado separadamente no SIAFI ou erro "
            "material do emissor da nota fiscal."
        )

        sig_id = f"SIG-DUPDOC-{compute_sha256_text(f'{supplier_doc}:{clean_doc_num}:{len(items)}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-DUPLICATE-EXPENSE-DOCUMENT",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                metric_name="duplicate_document_count",
                metric_value=Decimal(str(len(items))),
                threshold_value=Decimal("1.00"),
                audited_amount=total_amount,
                provenance_hashes=unique_hashes,
                requires_human_review=True,
            )
        )

    return signals


def evaluate_temporal_geographic_overlap_rule(
    expenses: Sequence[CuratedPublicExpense],
) -> list[AuditSignal]:
    """Identifica despesas presenciais concomitantes em UFs distintas para o mesmo agente na mesma data (`SPEC-0010`).

    Código da Regra: R-TEMPORAL-GEOGRAPHIC-OVERLAP
    """
    groups: dict[tuple[str, date], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.net_amount <= Decimal("0") or not exp.issue_date or not exp.state_uf or exp.state_uf == "BR":
            continue
        cat_upper = exp.expense_category.upper()
        if not any(kw in cat_upper for kw in _PHYSICAL_PRESENCE_KEYWORDS):
            continue
        groups[(exp.public_agent_id, exp.issue_date)].append(exp)

    signals: list[AuditSignal] = []

    for (agent_id, dt), items in groups.items():
        distinct_states = {e.state_uf for e in items}
        if len(distinct_states) < 2:
            continue

        total_amount = sum(e.net_amount for e in items)
        clean_agent = sanitize_untrusted_text(items[0].public_agent_name, 80)
        clean_id = sanitize_untrusted_text(agent_id, 40)
        states_str = ", ".join(sorted(distinct_states))
        date_str = dt.isoformat()
        unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in items}))

        title = f"Despesas presenciais concomitantes em UFs distintas para {clean_agent}"
        fact_summary = (
            f"O agente {clean_agent} ({clean_id}) registrou {len(items)} despesas presenciais em estados distintos "
            f"({states_str}) na data {date_str}, totalizando R$ {total_amount:.2f}."
        )
        stat_summary = (
            f"Concomitância de despesas com presença física exigida em {len(distinct_states)} UFs na mesma data."
        )
        scope_limit = (
            "A concomitância de despesas em diferentes estados na mesma data pode corresponder a atividades "
            "executadas por assessores autorizados do gabinete parlamentar em missões oficiais simultâneas sob "
            "o mesmo registro orçamentário do titular."
        )

        sig_id = f"SIG-GEO-{compute_sha256_text(f'{agent_id}:{date_str}:{states_str}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-TEMPORAL-GEOGRAPHIC-OVERLAP",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                metric_name="distinct_states_same_day_count",
                metric_value=Decimal(str(len(distinct_states))),
                threshold_value=Decimal("1.00"),
                audited_amount=total_amount,
                provenance_hashes=unique_hashes,
                requires_human_review=True,
            )
        )

    return signals


def compute_easter_sunday(year: int) -> date:
    """Calcula a data do Domingo de Páscoa pelo Algoritmo Meeus/Butcher (calendário Gregoriano)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_brazilian_national_holidays(year: int) -> set[date]:
    """Retorna o conjunto de feriados nacionais brasileiros (fixos e móveis).

    Feriados fixos federais (Leis nº 662/1949, 10.607/2002 e 14.759/2023):
    - 01/01: Confraternização Universal
    - 21/04: Tiradentes
    - 01/05: Dia Mundial do Trabalho
    - 07/09: Independência do Brasil
    - 12/10: Nossa Senhora Aparecida
    - 02/11: Finados
    - 15/11: Proclamação da República
    - 20/11: Dia Nacional de Zumbi e da Consciência Negra
    - 25/12: Natal

    Feriados móveis derivados da Páscoa:
    - Carnaval (terça-feira): Páscoa - 47 dias
    - Sexta-feira Santa (Paixão de Cristo): Páscoa - 2 dias
    - Páscoa: Domingo de Páscoa
    - Corpus Christi: Páscoa + 60 dias
    """
    fixed = {
        date(year, 1, 1),
        date(year, 4, 21),
        date(year, 5, 1),
        date(year, 9, 7),
        date(year, 10, 12),
        date(year, 11, 2),
        date(year, 11, 15),
        date(year, 11, 20),
        date(year, 12, 25),
    }
    easter = compute_easter_sunday(year)
    mobile = {
        easter - timedelta(days=47),  # Terça-feira de Carnaval
        easter - timedelta(days=2),   # Sexta-feira Santa
        easter,                        # Páscoa
        easter + timedelta(days=60),  # Corpus Christi
    }
    return fixed | mobile


def is_weekend_or_holiday(d: date) -> tuple[bool, str]:
    """Retorna se uma data é fim de semana (sábado/domingo) ou feriado nacional oficial."""
    if d.weekday() == 5:
        return True, "Sábado"
    if d.weekday() == 6:
        return True, "Domingo"
    holidays = get_brazilian_national_holidays(d.year)
    if d in holidays:
        return True, "Feriado Nacional"
    return False, ""


def is_parliamentary_recess(d: date) -> tuple[bool, str]:
    """Verifica se uma data recai nos períodos regimentais de recesso parlamentar (art. 57, CF/88)."""
    if d.month == 7 and 18 <= d.day <= 31:
        return True, "Recesso de Inverno (18 a 31 de julho)"
    if (d.month == 12 and d.day >= 23) or (d.month == 1) or (d.month == 2 and d.day == 1):
        return True, "Recesso de Verão (23 de dezembro a 1º de fevereiro)"
    return False, ""


def evaluate_weekend_holiday_expense_rule(
    expenses: Sequence[CuratedPublicExpense],
) -> list[AuditSignal]:
    """Identifica despesas presenciais emitidas em fins de semana e feriados nacionais oficiais.

    Código da Regra: R-TEMPORAL-WEEKEND-HOLIDAY
    Classificação Epistêmica: STATISTICAL_ANOMALY
    """
    signals: list[AuditSignal] = []

    for exp in expenses:
        if exp.net_amount <= Decimal("0") or not exp.issue_date:
            continue
        cat_upper = exp.expense_category.upper()
        if not any(kw in cat_upper for kw in _PHYSICAL_PRESENCE_KEYWORDS):
            continue

        is_non_working, day_desc = is_weekend_or_holiday(exp.issue_date)
        if not is_non_working:
            continue

        clean_agent = sanitize_untrusted_text(exp.public_agent_name, 80)
        clean_id = sanitize_untrusted_text(exp.public_agent_id, 40)
        clean_cat = sanitize_untrusted_text(exp.expense_category, 60)
        date_str = exp.issue_date.isoformat()

        title = f"Despesa presencial em dia não útil ({day_desc}) para {clean_agent}"
        fact_summary = (
            f"O agente {clean_agent} ({clean_id}) registrou despesa presencial de '{clean_cat}' "
            f"no valor de R$ {exp.net_amount:.2f} emitida em {date_str} ({day_desc}), documento fiscal {exp.document_number}."
        )
        stat_summary = (
            f"Emissão de despesa presencial em {day_desc.lower()}, dia atípico para atividades legislativas "
            f"deliberativas ordinárias presenciais no Congresso Nacional."
        )
        scope_limit = (
            "O exercício do mandato parlamentar estende-se aos finais de semana e feriados em razão de "
            "reuniões comunitárias, visitas a municípios e representação partidária na base eleitoral, "
            "sendo admitidas despesas indenizatórias compatíveis com o mandato."
        )

        sig_id = f"SIG-TMP-{compute_sha256_text(f'{exp.natural_key}:{date_str}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-TEMPORAL-WEEKEND-HOLIDAY",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                metric_name="is_non_working_day",
                metric_value=Decimal("1.00"),
                threshold_value=Decimal("0.00"),
                audited_amount=exp.net_amount,
                provenance_hashes=(exp.provenance.raw_batch_sha256,),
                requires_human_review=True,
            )
        )

    return signals


def evaluate_parliamentary_recess_expense_rule(
    expenses: Sequence[CuratedPublicExpense],
    recess_threshold_brl: Decimal = Decimal("15000.00"),
    min_expense_count: int = 3,
) -> list[AuditSignal]:
    """Identifica concentrações de despesas públicas acumuladas durante recessos parlamentares constitucionais.

    Código da Regra: R-TEMPORAL-PARLIAMENTARY-RECESS
    Classificação Epistêmica: STATISTICAL_ANOMALY
    """
    groups: dict[tuple[str, str, str], list[CuratedPublicExpense]] = defaultdict(list)

    for exp in expenses:
        if exp.net_amount <= Decimal("0") or not exp.issue_date or not exp.public_agent_id:
            continue
        is_recess, label = is_parliamentary_recess(exp.issue_date)
        if not is_recess:
            continue

        d = exp.issue_date
        if d.month == 7:
            cycle_id = f"INVERNO_{d.year}"
        elif d.month == 12:
            cycle_id = f"VERAO_{d.year}_{d.year + 1}"
        else:
            cycle_id = f"VERAO_{d.year - 1}_{d.year}"

        groups[(exp.public_agent_id, cycle_id, label)].append(exp)

    signals: list[AuditSignal] = []

    for (agent_id, cycle_id, label), items in groups.items():
        total_amount = sum(e.net_amount for e in items)
        if total_amount < recess_threshold_brl or len(items) < min_expense_count:
            continue

        clean_agent = sanitize_untrusted_text(items[0].public_agent_name, 80)
        clean_id = sanitize_untrusted_text(agent_id, 40)
        unique_hashes = tuple(sorted({e.provenance.raw_batch_sha256 for e in items}))

        title = f"Concentração de despesas durante {label.split(' (')[0]} para {clean_agent}"
        fact_summary = (
            f"O agente {clean_agent} ({clean_id}) registrou {len(items)} despesas totalizando "
            f"R$ {total_amount:.2f} durante o {label} no ciclo {cycle_id}."
        )
        stat_summary = (
            f"Volume acumulado de R$ {total_amount:.2f} distribuído em {len(items)} reembolsos durante o "
            f"período de recesso legislativo, superando o limiar de relevância de R$ {recess_threshold_brl:.2f}."
        )
        scope_limit = (
            "A ocorrência de despesas no recesso constitucional não configura infração orçamentária por si só. "
            "Atividades de gabinete, comunicação parlamentar, manutenção de escritórios estaduais e agendas em "
            "bases eleitorais mantêm-se em funcionamento durante o período de suspensão das sessões plenárias."
        )

        sig_id = f"SIG-REC-{compute_sha256_text(f'{agent_id}:{cycle_id}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-TEMPORAL-PARLIAMENTARY-RECESS",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                metric_name="recess_accumulated_amount_brl",
                metric_value=total_amount,
                threshold_value=recess_threshold_brl,
                audited_amount=total_amount,
                provenance_hashes=unique_hashes,
                requires_human_review=True,
            )
        )

    return signals


def evaluate_electoral_donor_supplier_crossmatch_rule(
    expenses: Sequence[CuratedPublicExpense],
    donations: Sequence[CuratedElectoralDonation],
) -> list[AuditSignal]:
    """Identifica quando um fornecedor de despesa pública consta como doador declarado de campanha eleitoral do mandatário.

    Código da Regra: R-CROSS-ELECTORAL-DONOR-SUPPLIER
    Classificação Epistêmica: CROSS_SOURCE_DIVERGENCE
    """
    donations_map: dict[tuple[str, str], list[CuratedElectoralDonation]] = defaultdict(list)
    for don in donations:
        if don.donor_doc_type != "CNPJ" or len(don.donor_doc_normalized) != 14:
            continue
        donations_map[(don.candidate_id, don.donor_doc_normalized)].append(don)

    matched_expenses: dict[tuple[str, str], list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.net_amount <= Decimal("0") or not exp.public_agent_id or not exp.supplier_doc_normalized:
            continue
        if exp.supplier_doc_type != "CNPJ" or len(exp.supplier_doc_normalized) != 14:
            continue
        pair = (exp.public_agent_id, exp.supplier_doc_normalized)
        if pair in donations_map:
            matched_expenses[pair].append(exp)

    signals: list[AuditSignal] = []

    for (agent_id, sup_doc), exp_items in matched_expenses.items():
        don_items = donations_map[(agent_id, sup_doc)]
        total_donated = sum(d.donation_amount for d in don_items)
        total_disbursed = sum(e.net_amount for e in exp_items)

        clean_agent = sanitize_untrusted_text(exp_items[0].public_agent_name, 80)
        clean_id = sanitize_untrusted_text(agent_id, 40)
        clean_supplier = sanitize_untrusted_text(exp_items[0].supplier_name, 120)

        dual_hashes = tuple(
            sorted(
                {d.provenance.raw_batch_sha256 for d in don_items}
                | {e.provenance.raw_batch_sha256 for e in exp_items}
            )
        )

        title = f"Fornecedor identificado como doador de campanha eleitoral para {clean_agent}"
        fact_summary = (
            f"O fornecedor {clean_supplier} ({sup_doc}) consta na prestação de contas do TSE com doação declarada "
            f"de R$ {total_donated:.2f} para o agente público {clean_agent} ({clean_id}) e posteriormente recebeu "
            f"R$ {total_disbursed:.2f} em {len(exp_items)} reembolsos de despesa pública."
        )
        stat_summary = (
            f"Convergência cadastral e financeira entre doação eleitoral e recebimento de recursos da cota/contrato "
            f"pelo mesmo CNPJ ({sup_doc}) no valor de R$ {total_disbursed:.2f}."
        )
        scope_limit = (
            "Doações de campanha eleitoral declaradas perante o TSE e prestação de serviços ou fornecimento para "
            "gabinetes parlamentares são atos legais regulamentados. O apontamento reflete cruzamento objetivo entre fontes "
            "oficiais distintas, não constituindo presunção de irregularidade, favoritismo indevido ou ilicitude."
        )

        sig_id = f"SIG-ELC-{compute_sha256_text(f'{agent_id}:{sup_doc}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-CROSS-ELECTORAL-DONOR-SUPPLIER",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                metric_name="electoral_donation_amount_brl",
                metric_value=total_donated,
                threshold_value=Decimal("0.00"),
                audited_amount=total_disbursed,
                provenance_hashes=dual_hashes,
                requires_human_review=True,
            )
        )

    return signals


def evaluate_qsa_shared_partner_rule(
    organ_code: str,
    organ_name: str,
    expenses: Sequence[CuratedPublicExpense],
    qsa_records: Sequence[CuratedCorporateMemberRecord],
    min_suppliers_count: int = 2,
) -> AuditSignal | None:
    """Identifica sócios administradores comuns em fornecedores distintos contratados pelo mesmo órgão (SPEC-0013).

    Código da Regra: R-CROSS-QSA-SHARED-PARTNER
    """
    if not expenses or not qsa_records:
        return None

    supplier_expenses: dict[str, list[CuratedPublicExpense]] = defaultdict(list)
    for exp in expenses:
        if exp.organ_code == organ_code and exp.net_amount > Decimal("0"):
            root = extract_cnpj_root(exp.supplier_doc_normalized)
            if root is not None:
                supplier_expenses[exp.supplier_doc_normalized].append(exp)

    if len(supplier_expenses) < min_suppliers_count:
        return None

    partner_to_suppliers: dict[tuple[str, str], set[str]] = defaultdict(set)
    partner_qsa_map: dict[tuple[str, str], list[CuratedCorporateMemberRecord]] = defaultdict(list)

    for qsa in qsa_records:
        for sup_doc in supplier_expenses:
            root = extract_cnpj_root(sup_doc)
            if qsa.corporate_root_cnpj == root or qsa.full_cnpj_normalized == sup_doc:
                key = (qsa.member_name_raw.strip(), qsa.member_doc_masked.strip())
                partner_to_suppliers[key].add(sup_doc)
                partner_qsa_map[key].append(qsa)

    for (p_name, p_doc), sup_set in partner_to_suppliers.items():
        if len(sup_set) >= min_suppliers_count:
            affected_expenses: list[CuratedPublicExpense] = []
            for s_doc in sup_set:
                affected_expenses.extend(supplier_expenses[s_doc])

            total_amount = sum(e.net_amount for e in affected_expenses)
            qsa_recs = partner_qsa_map[(p_name, p_doc)]
            hashes = set(q.provenance.raw_batch_sha256 for q in qsa_recs) | set(
                e.provenance.raw_batch_sha256 for e in affected_expenses
            )

            clean_organ = sanitize_untrusted_text(organ_name, 100)
            clean_partner = sanitize_untrusted_text(p_name, 100)
            suppliers_desc = ", ".join(sorted(sup_set))

            title = f"Sócio comum identificado em múltiplos fornecedores contratados por {clean_organ}"
            fact_summary = (
                f"O sócio {clean_partner} ({p_doc}) consta no QSA de {len(sup_set)} fornecedores distintos "
                f"({suppliers_desc}) que receberam pagamentos de {clean_organ} totalizando R$ {total_amount:.2f}."
            )
            stat_summary = (
                f"Convergência societária cadastral identificada via base do CNPJ da Receita Federal em {len(sup_set)} "
                f"pessoas jurídicas contratadas pelo mesmo órgão com R$ {total_amount:.2f} despendidos."
            )
            scope_limit = (
                "A participação societária em múltiplos empreendimentos econômicos é permitida pela legislação brasileira. "
                "A identificação de sócio administrador comum em fornecedores não configura conluio ou infração automática, "
                "podendo refletir grupos societários estruturados em ramos econômicos correlatos."
            )

            sig_id = f"SIG-QSA-SHR-{compute_sha256_text(f'{organ_code}:{p_name}:{p_doc}')[:16]}"
            return AuditSignal(
                signal_id=sig_id,
                rule_code="R-CROSS-QSA-SHARED-PARTNER",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                metric_name="shared_partner_suppliers_count",
                metric_value=Decimal(str(len(sup_set))),
                threshold_value=Decimal(str(min_suppliers_count)),
                audited_amount=total_amount,
                provenance_hashes=tuple(sorted(hashes)),
                requires_human_review=True,
            )

    return None


def evaluate_qsa_individual_donor_rule(
    public_agent_id: str,
    expenses: Sequence[CuratedPublicExpense],
    qsa_records: Sequence[CuratedCorporateMemberRecord],
    donations: Sequence[CuratedElectoralDonation],
) -> AuditSignal | None:
    """Identifica doação eleitoral de pessoa física (sócio no QSA) para a campanha do mandatário contratante (SPEC-0013).

    Código da Regra: R-CROSS-QSA-DONOR-SUPPLIER
    """
    if not expenses or not qsa_records or not donations:
        return None

    agent_expenses = [e for e in expenses if e.public_agent_id == public_agent_id and e.net_amount > Decimal("0")]
    if not agent_expenses:
        return None

    supplier_expenses: dict[str, list[CuratedPublicExpense]] = defaultdict(list)
    for exp in agent_expenses:
        supplier_expenses[exp.supplier_doc_normalized].append(exp)

    agent_donations = [d for d in donations if d.candidate_id == public_agent_id and d.donation_amount > Decimal("0")]
    if not agent_donations:
        return None

    donation_map: dict[tuple[str, str], list[CuratedElectoralDonation]] = defaultdict(list)
    for don in agent_donations:
        donation_map[(don.donor_name.strip().upper(), don.donor_doc_normalized.strip())].append(don)

    for sup_doc, exp_items in supplier_expenses.items():
        root = extract_cnpj_root(sup_doc)
        if root is None:
            continue

        matching_qsa = [q for q in qsa_records if q.corporate_root_cnpj == root or q.full_cnpj_normalized == sup_doc]
        for qsa in matching_qsa:
            qsa_key = (qsa.member_name_raw.strip().upper(), qsa.member_doc_masked.strip())
            if qsa_key in donation_map:
                don_items = donation_map[qsa_key]
                total_donation = sum(d.donation_amount for d in don_items)
                total_expense = sum(e.net_amount for e in exp_items)

                clean_agent = sanitize_untrusted_text(exp_items[0].public_agent_name, 100)
                clean_partner = sanitize_untrusted_text(qsa.member_name_raw, 100)
                clean_supplier = sanitize_untrusted_text(exp_items[0].supplier_name, 120)

                triple_hashes = tuple(
                    sorted(
                        {qsa.provenance.raw_batch_sha256}
                        | {e.provenance.raw_batch_sha256 for e in exp_items}
                        | {d.provenance.raw_batch_sha256 for d in don_items}
                    )
                )

                title = f"Sócio de fornecedor público identificado como doador de campanha eleitoral de {clean_agent}"
                fact_summary = (
                    f"O sócio {clean_partner} ({qsa.member_doc_masked}) do fornecedor {clean_supplier} ({sup_doc}) "
                    f"realizou doação eleitoral declarada de R$ {total_donation:.2f} para a campanha de {clean_agent} ({public_agent_id}), "
                    f"tendo o fornecedor recebido R$ {total_expense:.2f} em pagamentos públicos do mandatário."
                )
                stat_summary = (
                    f"Cruzamento triplo entre quadro societário da Receita Federal (QSA), despesas públicas ({sup_doc}) "
                    f"e prestação de contas eleitorais de pessoa física no TSE vinculadas ao mandatário."
                )
                scope_limit = (
                    "Doações eleitorais declaradas por pessoas físicas e a contratação de pessoas jurídicas de fornecimento são atos "
                    "legalmente autorizados. A realização de doação de campanha como pessoa física dentro dos limites legais e a contratação "
                    "do fornecedor não presumem favorecimento indevido ou desvio de finalidade."
                )

                sig_id = f"SIG-QSA-DON-{compute_sha256_text(f'{public_agent_id}:{sup_doc}:{qsa.member_doc_masked}')[:16]}"
                return AuditSignal(
                    signal_id=sig_id,
                    rule_code="R-CROSS-QSA-DONOR-SUPPLIER",
                    title=title,
                    official_fact_summary=fact_summary,
                    statistical_inference_summary=stat_summary,
                    scope_limitation_summary=scope_limit,
                    epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                    metric_name="individual_partner_donation_amount_brl",
                    metric_value=total_donation,
                    threshold_value=Decimal("0.00"),
                    audited_amount=total_expense,
                    provenance_hashes=triple_hashes,
                    requires_human_review=True,
                )

    return None


def evaluate_recent_company_creation_rule(
    companies: Sequence[CuratedCompanyRegistrationRecord],
    expenses: Sequence[CuratedPublicExpense] | None = None,
    contracts: Sequence[CuratedPublicContract] | None = None,
    max_age_days: int = 180,
    min_amount_threshold: Decimal = Decimal("50000.00"),
) -> list[AuditSignal]:
    """Identifica contratações públicas celebradas com empresas recém-constituídas (< 180 dias) (SPEC-0014).

    Código da Regra: R-CORP-RECENT-CREATION
    """
    if not companies or (not expenses and not contracts):
        return []

    company_by_cnpj: dict[str, CuratedCompanyRegistrationRecord] = {
        c.cnpj_normalized: c for c in companies
    }
    company_by_root: dict[str, CuratedCompanyRegistrationRecord] = {
        c.corporate_root_cnpj: c for c in companies
    }

    signals: list[AuditSignal] = []

    # 1. Avaliar contratos
    if contracts:
        for contract in contracts:
            if contract.current_amount < min_amount_threshold:
                continue
            supplier_doc = contract.supplier_doc_normalized
            company = company_by_cnpj.get(supplier_doc) or company_by_root.get(supplier_doc[:8])
            if not company:
                continue
            contract_dt = contract.signature_date
            if not contract_dt:
                continue
            age_days = (contract_dt - company.opening_date).days
            if 0 <= age_days < max_age_days:
                clean_organ = sanitize_untrusted_text(contract.organ_name, 100)
                clean_supplier = sanitize_untrusted_text(company.legal_name, 120)
                amount = contract.current_amount
                hashes = tuple(sorted({company.provenance.raw_batch_sha256, contract.provenance.raw_batch_sha256}))
                title = f"Contratação de empresa recém-constituída ({age_days} dias) por {clean_organ}"
                fact_summary = (
                    f"A empresa {clean_supplier} ({company.cnpj_normalized}), com data de abertura cadastral em "
                    f"{company.opening_date.strftime('%d/%m/%Y')}, celebrou contrato público de R$ {amount:.2f} com "
                    f"{clean_organ} em {contract_dt.strftime('%d/%m/%Y')}, apenas {age_days} dias após sua constituição formal."
                )
                stat_summary = (
                    f"A celebração do contrato ocorreu no intervalo de {age_days} dias da abertura cadastral da pessoa jurídica, "
                    f"inferior ao limiar de referência de {max_age_days} dias de maturidade operacional."
                )
                scope_limit = (
                    "A contratação de empresas recém-constituídas é juridicamente válida desde que atendidos os requisitos "
                    "de habilitação jurídica e qualificação técnica do edital. A abertura recente não comprova irregularidade, "
                    "podendo corresponder a consórcios de profissionais experientes ou reorganização societária legítima."
                )
                sig_id = f"SIG-REC-CORP-{compute_sha256_text(f'{contract.pncp_control_number}:{company.cnpj_normalized}:{age_days}')[:16]}"
                signals.append(
                    AuditSignal(
                        signal_id=sig_id,
                        rule_code="R-CORP-RECENT-CREATION",
                        title=title,
                        official_fact_summary=fact_summary,
                        statistical_inference_summary=stat_summary,
                        scope_limitation_summary=scope_limit,
                        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                        metric_name="company_age_days_at_contract",
                        metric_value=Decimal(str(age_days)),
                        threshold_value=Decimal(str(max_age_days)),
                        audited_amount=amount,
                        provenance_hashes=hashes,
                        requires_human_review=True,
                    )
                )

    # 2. Avaliar despesas
    if expenses:
        for exp in expenses:
            if exp.net_amount < min_amount_threshold:
                continue
            supplier_doc = exp.supplier_doc_normalized
            company = company_by_cnpj.get(supplier_doc) or company_by_root.get(supplier_doc[:8])
            if not company:
                continue
            exp_dt = exp.issue_date
            age_days = (exp_dt - company.opening_date).days
            if 0 <= age_days < max_age_days:
                clean_organ = sanitize_untrusted_text(exp.organ_name, 100)
                clean_supplier = sanitize_untrusted_text(company.legal_name, 120)
                amount = exp.net_amount
                hashes = tuple(sorted({company.provenance.raw_batch_sha256, exp.provenance.raw_batch_sha256}))
                title = f"Despesa pública realizada com empresa recém-constituída ({age_days} dias) em {clean_organ}"
                fact_summary = (
                    f"A empresa {clean_supplier} ({company.cnpj_normalized}), aberta em {company.opening_date.strftime('%d/%m/%Y')}, "
                    f"emitiu documento fiscal de R$ {amount:.2f} para {clean_organ} em {exp_dt.strftime('%d/%m/%Y')}, "
                    f"após {age_days} dias de sua constituição formal na Receita Federal."
                )
                stat_summary = (
                    f"Emissão de despesa pública de relevância material com apenas {age_days} dias decorridos desde o registro cadastral, "
                    f"abaixo do parâmetro de triagem de {max_age_days} dias."
                )
                scope_limit = (
                    "A emissão de nota fiscal por sociedade recém-constituída atende aos preceitos da liberdade de iniciativa. "
                    "O tempo decorrido desde a constituição cadastral constitui parâmetro de risco operacional, não implicando "
                    "impropriedade ou inexecução do serviço faturado."
                )
                sig_id = f"SIG-REC-EXP-{compute_sha256_text(f'{exp.natural_key}:{company.cnpj_normalized}:{age_days}')[:16]}"
                signals.append(
                    AuditSignal(
                        signal_id=sig_id,
                        rule_code="R-CORP-RECENT-CREATION",
                        title=title,
                        official_fact_summary=fact_summary,
                        statistical_inference_summary=stat_summary,
                        scope_limitation_summary=scope_limit,
                        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                        metric_name="company_age_days_at_contract",
                        metric_value=Decimal(str(age_days)),
                        threshold_value=Decimal(str(max_age_days)),
                        audited_amount=amount,
                        provenance_hashes=hashes,
                        requires_human_review=True,
                    )
                )

    return signals


def evaluate_low_capital_outlier_rule(
    companies: Sequence[CuratedCompanyRegistrationRecord],
    expenses: Sequence[CuratedPublicExpense] | None = None,
    contracts: Sequence[CuratedPublicContract] | None = None,
    max_ratio_threshold: Decimal = Decimal("50.00"),
    min_amount_threshold: Decimal = Decimal("100000.00"),
) -> list[AuditSignal]:
    """Identifica contratações ou despesas com montante desproporcional ao capital social declarado (>= 50x) (SPEC-0014).

    Código da Regra: R-CORP-LOW-CAPITAL-OUTLIER
    """
    if not companies or (not expenses and not contracts):
        return []

    company_by_cnpj: dict[str, CuratedCompanyRegistrationRecord] = {
        c.cnpj_normalized: c for c in companies if c.share_capital_brl > Decimal("0.00")
    }
    company_by_root: dict[str, CuratedCompanyRegistrationRecord] = {
        c.corporate_root_cnpj: c for c in companies if c.share_capital_brl > Decimal("0.00")
    }

    signals: list[AuditSignal] = []

    # 1. Contratos
    if contracts:
        for contract in contracts:
            if contract.current_amount < min_amount_threshold:
                continue
            sup_doc = contract.supplier_doc_normalized
            company = company_by_cnpj.get(sup_doc) or company_by_root.get(sup_doc[:8])
            if not company or company.share_capital_brl <= Decimal("0.00"):
                continue
            ratio = contract.current_amount / company.share_capital_brl
            if ratio >= max_ratio_threshold:
                clean_organ = sanitize_untrusted_text(contract.organ_name, 100)
                clean_supplier = sanitize_untrusted_text(company.legal_name, 120)
                amount = contract.current_amount
                hashes = tuple(sorted({company.provenance.raw_batch_sha256, contract.provenance.raw_batch_sha256}))
                title = f"Contrato público com razão atípica sobre o capital social ({ratio:.1f}x) em {clean_organ}"
                fact_summary = (
                    f"A empresa {clean_supplier} ({company.cnpj_normalized}), com capital social declarado de "
                    f"R$ {company.share_capital_brl:.2f}, celebrou contrato de R$ {amount:.2f} com {clean_organ}, "
                    f"equivalente a {ratio:.1f} vezes o patrimônio líquido inicial informado."
                )
                stat_summary = (
                    f"A razão entre o montante contratado e o capital social ({ratio:.1f}x) supera o limiar "
                    f"de referência de {max_ratio_threshold:.1f}x para triagem de risco de capacidade econômico-financeira."
                )
                scope_limit = (
                    "A legislação de licitações (Lei nº 14.133/2021) permite a comprovação de qualificação financeira "
                    "por índices contábeis de liquidez ou garantias contratuais alternativas. A razão elevada não constitui "
                    "superfaturamento ou vício formal, refletindo apenas indicador de análise de risco preventivo."
                )
                sig_id = f"SIG-CAP-CTR-{compute_sha256_text(f'{contract.pncp_control_number}:{company.cnpj_normalized}:{ratio:.2f}')[:16]}"
                signals.append(
                    AuditSignal(
                        signal_id=sig_id,
                        rule_code="R-CORP-LOW-CAPITAL-OUTLIER",
                        title=title,
                        official_fact_summary=fact_summary,
                        statistical_inference_summary=stat_summary,
                        scope_limitation_summary=scope_limit,
                        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                        metric_name="contract_to_share_capital_ratio",
                        metric_value=ratio.quantize(Decimal("0.01")),
                        threshold_value=max_ratio_threshold,
                        audited_amount=amount,
                        provenance_hashes=hashes,
                        requires_human_review=True,
                    )
                )

    # 2. Despesas agregadas por fornecedor
    if expenses:
        exp_by_supplier: dict[str, list[CuratedPublicExpense]] = defaultdict(list)
        for exp in expenses:
            exp_by_supplier[exp.supplier_doc_normalized].append(exp)

        for sup_doc, items in exp_by_supplier.items():
            total_exp = sum(e.net_amount for e in items)
            if total_exp < min_amount_threshold:
                continue
            company = company_by_cnpj.get(sup_doc) or company_by_root.get(sup_doc[:8])
            if not company or company.share_capital_brl <= Decimal("0.00"):
                continue
            ratio = total_exp / company.share_capital_brl
            if ratio >= max_ratio_threshold:
                clean_organ = sanitize_untrusted_text(items[0].organ_name, 100)
                clean_supplier = sanitize_untrusted_text(company.legal_name, 120)
                hashes = tuple(
                    sorted({company.provenance.raw_batch_sha256} | {e.provenance.raw_batch_sha256 for e in items})
                )
                title = f"Volume acumulado de pagamentos com razão atípica sobre o capital social ({ratio:.1f}x) em {clean_organ}"
                fact_summary = (
                    f"A empresa {clean_supplier} ({company.cnpj_normalized}), com capital social de R$ {company.share_capital_brl:.2f}, "
                    f"acumulou R$ {total_exp:.2f} em pagamentos públicos ({len(items)} despesas) de {clean_organ}, "
                    f"atingindo {ratio:.1f} vezes o capital registrado."
                )
                stat_summary = (
                    f"A relação entre despesas empenhadas e capital integralizado ({ratio:.1f}x) excede o patamar "
                    f"analítico de {max_ratio_threshold:.1f}x para acompanhamento de capacidade operacional."
                )
                scope_limit = (
                    "Empresas de prestação de serviços continuados sem demanda intensiva em capital fixo podem legitimamente "
                    "faturar montantes desproporcionais ao seu capital social original, sendo o fluxo de caixa sustentado "
                    "pelas medições contratuais periódicas."
                )
                sig_id = f"SIG-CAP-EXP-{compute_sha256_text(f'{items[0].organ_code}:{company.cnpj_normalized}:{ratio:.2f}')[:16]}"
                signals.append(
                    AuditSignal(
                        signal_id=sig_id,
                        rule_code="R-CORP-LOW-CAPITAL-OUTLIER",
                        title=title,
                        official_fact_summary=fact_summary,
                        statistical_inference_summary=stat_summary,
                        scope_limitation_summary=scope_limit,
                        epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                        metric_name="contract_to_share_capital_ratio",
                        metric_value=ratio.quantize(Decimal("0.01")),
                        threshold_value=max_ratio_threshold,
                        audited_amount=total_exp,
                        provenance_hashes=hashes,
                        requires_human_review=True,
                    )
                )

    return signals


HIGH_RISK_OBJECT_SECTORS: dict[str, tuple[str, ...]] = {
    # Engenharia e Construção Pesada (Divisões 41, 42, 43)
    "pavimentacao": ("41", "42", "43"),
    "terraplanagem": ("41", "42", "43"),
    "drenagem": ("41", "42", "43"),
    "asfalto": ("41", "42", "43"),
    "reforma predial": ("41", "42", "43"),
    "construcao": ("41", "42", "43"),
    "obras de engenharia": ("41", "42", "43"),
    # Tecnologia da Informação (Divisões 62, 63)
    "software": ("62", "63"),
    "sistema de informacao": ("62", "63"),
    "desenvolvimento web": ("62", "63"),
    "computacao em nuvem": ("62", "63"),
    "banco de dados": ("62", "63"),
    # Fretamento Aéreo e Locação de Aeronaves (Divisões 51, 77)
    "aeronave": ("51", "77"),
    "helicoptero": ("51", "77"),
    "fretamento aereo": ("51", "77"),
    # Serviços Hospitalares e Médicos (Divisão 86)
    "servicos medicos": ("86",),
    "atendimento hospitalar": ("86",),
    "analises clinicas": ("86",),
}


def evaluate_cnae_contract_incompatibility_rule(
    contracts: Sequence[CuratedPublicContract],
    companies: Sequence[CuratedCompanyRegistrationRecord],
    min_contract_threshold: Decimal = Decimal("50000.00"),
) -> list[AuditSignal]:
    """Regra `R-CORP-CNAE-INCOMPATIBLE` (SPEC-0015):
    Identifica contratações públicas onde o objeto adjudicado de alta especificidade técnica
    é materialmente incompatível com as atividades econômicas cadastradas da empresa (CNAE principal
    e tupla de secundários perante a Receita Federal).
    """
    if not contracts or not companies:
        return []

    company_by_cnpj = {c.cnpj_normalized: c for c in companies}
    company_by_root = {c.corporate_root_cnpj: c for c in companies}

    signals: list[AuditSignal] = []

    for contract in contracts:
        if contract.current_amount < min_contract_threshold:
            continue

        company = company_by_cnpj.get(contract.supplier_doc_normalized) or company_by_root.get(
            contract.supplier_doc_normalized[:8]
        )
        if not company:
            continue

        obj_lower = contract.contract_object.lower()

        # Determinar divisões necessárias com base no objeto contratual
        required_divisions: set[str] = set()
        for keyword, divs in HIGH_RISK_OBJECT_SECTORS.items():
            if keyword in obj_lower:
                required_divisions.update(divs)

        if not required_divisions:
            # Não é objeto de alta especificidade monitorado
            continue

        # Coletar divisões da empresa (CNAE principal e secundários)
        company_divisions: set[str] = set()
        if len(company.cnae_main_code) >= 2:
            company_divisions.add(company.cnae_main_code[:2])
        for sec in company.secondary_cnae_codes:
            if len(sec) >= 2:
                company_divisions.add(sec[:2])

        # Se houver qualquer interseção, a empresa é compatível
        if company_divisions & required_divisions:
            continue

        # Incompatibilidade material constatada
        clean_supplier = sanitize_untrusted_text(company.legal_name, 120)
        clean_organ = sanitize_untrusted_text(contract.organ_name, 100)
        clean_object = sanitize_untrusted_text(contract.contract_object, 120)

        hashes = tuple(
            sorted({company.provenance.raw_batch_sha256, contract.provenance.raw_batch_sha256})
        )

        secondaries_desc = ", ".join(company.secondary_cnae_codes) if company.secondary_cnae_codes else "nenhum"
        req_divs_desc = ", ".join(sorted(required_divisions))

        title = f"Incompatibilidade entre atividade econômica CNAE ({company.cnae_main_code}) e objeto contratado em {clean_organ}"
        fact_summary = (
            f"Contrato formalizado no montante de R$ {contract.current_amount:.2f} com a empresa {clean_supplier} "
            f"({company.cnpj_normalized}) para o objeto '{clean_object}'. A empresa possui CNAE principal "
            f"{company.cnae_main_code} e secundários [{secondaries_desc}], sem registro das divisões CNAE "
            f"afins ao objeto ({req_divs_desc})."
        )
        stat_summary = (
            f"Detecção determinística de incompatibilidade entre as atividades econômicas oficiais registradas "
            f"no cadastro da Receita Federal e o objeto contratual licitado (limiar mínimo de relevância: "
            f"R$ {min_contract_threshold:.2f})."
        )
        scope_limit = (
            "A Classificação Nacional de Atividades Econômicas (CNAE) tem finalidade prioritariamente tributária "
            "e estatística perante a administração fiscal. A divergência cadastral não comprova incapacidade "
            "operacional nem nulidade do contrato, podendo a empresa ter capacidade técnica comprovada em atestados "
            "ou estar em processo de atualização societária perante a Junta Comercial."
        )

        sig_id = f"SIG-CNAE-{compute_sha256_text(f'{contract.pncp_control_number}:{company.cnpj_normalized}:{clean_object}')[:16]}"
        signals.append(
            AuditSignal(
                signal_id=sig_id,
                rule_code="R-CORP-CNAE-INCOMPATIBLE",
                title=title,
                official_fact_summary=fact_summary,
                statistical_inference_summary=stat_summary,
                scope_limitation_summary=scope_limit,
                epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
                metric_name="cnae_sectoral_incompatibility_flag",
                metric_value=Decimal("1.00"),
                threshold_value=Decimal("0.00"),
                audited_amount=contract.current_amount,
                provenance_hashes=hashes,
                requires_human_review=True,
            )
        )

    return signals


def evaluate_public_agent_supplier_crossmatch_rule(
    agents: Sequence[CuratedPublicAgentRecord],
    corporate_members: Sequence[CuratedCorporateMemberRecord],
    contracts: Sequence[CuratedPublicContract] = (),
    expenses: Sequence[CuratedPublicExpense] = (),
) -> list[AuditSignal]:
    """Identifica agentes públicos ou dirigentes societários de fornecedores contratados pelo próprio órgão (SPEC-0016 / Lei 14.133/2021).

    Código da Regra: R-CROSS-PUBLIC-AGENT-SUPPLIER
    """
    if not agents or not corporate_members or (not contracts and not expenses):
        return []

    # Mapear agentes públicos por chave de identificação: (nome_normalizado, cpf_mascarado) -> list[CuratedPublicAgentRecord]
    agents_by_person: dict[tuple[str, str], list[CuratedPublicAgentRecord]] = defaultdict(list)
    for agent in agents:
        clean_name = " ".join(agent.agent_name.strip().upper().split())
        clean_doc = agent.agent_doc_masked.strip()
        agents_by_person[(clean_name, clean_doc)].append(agent)

    def _clean_organ(code: str) -> str:
        return code.strip().replace(".", "").replace("/", "").replace("-", "")

    signals: list[AuditSignal] = []
    seen_signals: set[str] = set()

    # 1. Cruzar com contratos públicos
    for contract in contracts:
        sup_doc = contract.supplier_doc_normalized.strip()
        root = extract_cnpj_root(sup_doc)
        contract_organ_clean = _clean_organ(contract.organ_cnpj)

        matching_qsa = [
            q for q in corporate_members
            if (root is not None and q.corporate_root_cnpj == root) or q.full_cnpj_normalized == sup_doc
        ]

        for qsa in matching_qsa:
            qsa_name = " ".join(qsa.member_name_raw.strip().upper().split())
            qsa_doc = qsa.member_doc_masked.strip()
            person_key = (qsa_name, qsa_doc)

            if person_key in agents_by_person:
                matched_agents = agents_by_person[person_key]
                for agent in matched_agents:
                    agent_organ_clean = _clean_organ(agent.organ_code)
                    # Exigência legal estrita: agente público deve pertencer ao MESMO órgão contratante
                    if agent_organ_clean != contract_organ_clean:
                        continue

                    signal_key = f"{agent.agent_id}:{sup_doc}:{contract.pncp_control_number}"
                    if signal_key in seen_signals:
                        continue
                    seen_signals.add(signal_key)

                    clean_agent_name = sanitize_untrusted_text(agent.agent_name, 120)
                    clean_organ_name = sanitize_untrusted_text(contract.organ_name, 150)
                    clean_supplier = sanitize_untrusted_text(contract.supplier_name, 150)
                    clean_position = sanitize_untrusted_text(agent.position_title, 100)

                    provenance_hashes = tuple(
                        sorted(
                            {agent.provenance.raw_batch_sha256}
                            | {qsa.provenance.raw_batch_sha256}
                            | {contract.provenance.raw_batch_sha256}
                        )
                    )

                    title = f"Agente público do próprio órgão identificado no quadro societário de fornecedor contratado em {clean_organ_name}"
                    fact_summary = (
                        f"O agente público {clean_agent_name} ({agent.agent_doc_masked}, cargo: {clean_position}), "
                        f"vinculado ao órgão {clean_organ_name} ({contract.organ_cnpj}), figura como sócio/administrador "
                        f"no QSA do fornecedor contratado {clean_supplier} ({sup_doc}) no contrato {contract.pncp_control_number} "
                        f"no valor de R$ {contract.current_amount:.2f}."
                    )
                    stat_summary = (
                        f"Cruzamento determinístico multicritério entre cadastro de servidores públicos "
                        f"({agent.provenance.source.value}), Quadro de Sócios e Administradores (QSA/Receita Federal) "
                        f"e contratos públicos (PNCP) com coincidência de órgão ({contract.organ_cnpj})."
                    )
                    scope_limit = (
                        "O art. 9º, § 1º da Lei nº 14.133/2021 e a Súmula TCU nº 269 vedam a participação direta ou "
                        "indireta em licitação e execução contratual de agentes públicos vinculados ao órgão licitante. "
                        "O art. 117, X da Lei nº 8.112/1990 veda gerência de sociedade privada a servidores, admitindo "
                        "participação como cotista sem poder de gestão. A indicação cadastral nominal não presume "
                        "irregularidade automática, exigindo procedimento preliminar formal para averiguar efetivo exercício "
                        "de gestão, licenças não remuneradas ou eventual homonímia antes de qualquer juízo de responsabilidade."
                    )

                    sig_id = f"SIG-PUB-AGENT-{compute_sha256_text(signal_key)[:16]}"
                    signals.append(
                        AuditSignal(
                            signal_id=sig_id,
                            rule_code="R-CROSS-PUBLIC-AGENT-SUPPLIER",
                            title=title,
                            official_fact_summary=fact_summary,
                            statistical_inference_summary=stat_summary,
                            scope_limitation_summary=scope_limit,
                            epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                            metric_name="contracted_amount_with_agent_partner_brl",
                            metric_value=contract.current_amount,
                            threshold_value=Decimal("0.00"),
                            audited_amount=contract.current_amount,
                            provenance_hashes=provenance_hashes,
                            requires_human_review=True,
                        )
                    )

    # 2. Cruzar com despesas públicas
    for expense in expenses:
        if expense.net_amount <= Decimal("0.00"):
            continue
        sup_doc = expense.supplier_doc_normalized.strip()
        root = extract_cnpj_root(sup_doc)
        expense_organ_clean = _clean_organ(expense.organ_code)

        matching_qsa = [
            q for q in corporate_members
            if (root is not None and q.corporate_root_cnpj == root) or q.full_cnpj_normalized == sup_doc
        ]

        for qsa in matching_qsa:
            qsa_name = " ".join(qsa.member_name_raw.strip().upper().split())
            qsa_doc = qsa.member_doc_masked.strip()
            person_key = (qsa_name, qsa_doc)

            if person_key in agents_by_person:
                matched_agents = agents_by_person[person_key]
                for agent in matched_agents:
                    agent_organ_clean = _clean_organ(agent.organ_code)
                    if agent_organ_clean != expense_organ_clean:
                        continue

                    signal_key = f"{agent.agent_id}:{sup_doc}:{expense.natural_key}"
                    if signal_key in seen_signals:
                        continue
                    seen_signals.add(signal_key)

                    clean_agent_name = sanitize_untrusted_text(agent.agent_name, 120)
                    clean_organ_name = sanitize_untrusted_text(expense.organ_name, 150)
                    clean_supplier = sanitize_untrusted_text(expense.supplier_name, 150)
                    clean_position = sanitize_untrusted_text(agent.position_title, 100)

                    provenance_hashes = tuple(
                        sorted(
                            {agent.provenance.raw_batch_sha256}
                            | {qsa.provenance.raw_batch_sha256}
                            | {expense.provenance.raw_batch_sha256}
                        )
                    )

                    title = f"Agente público do próprio órgão identificado no quadro societário de favorecido de despesa em {clean_organ_name}"
                    fact_summary = (
                        f"O agente público {clean_agent_name} ({agent.agent_doc_masked}, cargo: {clean_position}), "
                        f"vinculado ao órgão {clean_organ_name} ({expense.organ_code}), figura como sócio/administrador "
                        f"no QSA do fornecedor favorecido {clean_supplier} ({sup_doc}) em despesa liquidada "
                        f"no valor de R$ {expense.net_amount:.2f}."
                    )
                    stat_summary = (
                        f"Cruzamento determinístico multicritério entre cadastro de servidores públicos "
                        f"({agent.provenance.source.value}), Quadro de Sócios e Administradores (QSA/Receita Federal) "
                        f"e despesas públicas ({expense.provenance.source.value}) com coincidência de órgão ({expense.organ_code})."
                    )
                    scope_limit = (
                        "O art. 9º, § 1º da Lei nº 14.133/2021 e a Súmula TCU nº 269 vedam a participação direta ou "
                        "indireta em licitação e execução contratual de agentes públicos vinculados ao órgão licitante. "
                        "O art. 117, X da Lei nº 8.112/1990 veda gerência de sociedade privada a servidores, admitindo "
                        "participação como cotista sem poder de gestão. A indicação cadastral nominal não presume "
                        "irregularidade automática, exigindo procedimento preliminar formal para averiguar efetivo exercício "
                        "de gestão, licenças não remuneradas ou eventual homonímia antes de qualquer juízo de responsabilidade."
                    )

                    sig_id = f"SIG-PUB-AGENT-{compute_sha256_text(signal_key)[:16]}"
                    signals.append(
                        AuditSignal(
                            signal_id=sig_id,
                            rule_code="R-CROSS-PUBLIC-AGENT-SUPPLIER",
                            title=title,
                            official_fact_summary=fact_summary,
                            statistical_inference_summary=stat_summary,
                            scope_limitation_summary=scope_limit,
                            epistemic_layer=EpistemicClassification.CROSS_SOURCE_DIVERGENCE,
                            metric_name="contracted_amount_with_agent_partner_brl",
                            metric_value=expense.net_amount,
                            threshold_value=Decimal("0.00"),
                            audited_amount=expense.net_amount,
                            provenance_hashes=provenance_hashes,
                            requires_human_review=True,
                        )
                    )

    return signals



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

from deolhonobrasil.audit.statistics import calculate_hhi_concentration, calculate_z_score
from deolhonobrasil.pipeline.models import (
    CuratedPublicContract,
    CuratedPublicExpense,
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

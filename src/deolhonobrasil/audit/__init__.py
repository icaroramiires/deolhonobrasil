"""Módulo de Auditoria Determinística, Detecção de Anomalias Estatísticas e Decisão Laya.

Exporta as interfaces públicas da Fase 4:
- Estatística: calculate_z_score, calculate_mad_z_score, calculate_hhi_concentration, evaluate_benford_first_digit.
- Regras determinísticas: AuditSignal, evaluate_contract_overpricing_rule, evaluate_supplier_concentration_rule, evaluate_ceap_quota_outlier_rule.
- Motor Laya System 1: TriageAction, System1Decision, DecisionEnginePort, LayaSystem1Adapter.
- Narrador aterrado: GroundedDossierSection, GroundedDossierNarrator.
"""

from deolhonobrasil.audit.laya_engine import (
    DecisionEnginePort,
    LayaSystem1Adapter,
    System1Decision,
    TriageAction,
)
from deolhonobrasil.audit.rag_narrator import (
    GroundedDossierNarrator,
    GroundedDossierSection,
)
from deolhonobrasil.audit.rules import (
    AuditSignal,
    compute_easter_sunday,
    evaluate_amendment_execution_divergence_rule,
    evaluate_benford_distribution_rule,
    evaluate_ceap_quota_outlier_rule,
    evaluate_ceis_cnep_sanctioned_supplier_rule,
    evaluate_contract_overpricing_rule,
    evaluate_duplicate_expense_document_rule,
    evaluate_monopolistic_supplier_category_rule,
    evaluate_parliamentary_recess_expense_rule,
    evaluate_shared_cnpj_root_rule,
    evaluate_split_expense_rule,
    evaluate_supplier_concentration_rule,
    evaluate_temporal_geographic_overlap_rule,
    evaluate_weekend_holiday_expense_rule,
    extract_cnpj_root,
    get_brazilian_national_holidays,
    is_parliamentary_recess,
    is_weekend_or_holiday,
)
from deolhonobrasil.audit.statistics import (
    calculate_hhi_concentration,
    calculate_mad_z_score,
    calculate_z_score,
    evaluate_benford_first_digit,
)

__all__ = [
    "AuditSignal",
    "DecisionEnginePort",
    "GroundedDossierNarrator",
    "GroundedDossierSection",
    "LayaSystem1Adapter",
    "System1Decision",
    "TriageAction",
    "calculate_hhi_concentration",
    "calculate_mad_z_score",
    "calculate_z_score",
    "evaluate_amendment_execution_divergence_rule",
    "evaluate_benford_distribution_rule",
    "evaluate_benford_first_digit",
    "evaluate_ceap_quota_outlier_rule",
    "evaluate_ceis_cnep_sanctioned_supplier_rule",
    "evaluate_contract_overpricing_rule",
    "evaluate_duplicate_expense_document_rule",
    "evaluate_monopolistic_supplier_category_rule",
    "evaluate_parliamentary_recess_expense_rule",
    "evaluate_shared_cnpj_root_rule",
    "evaluate_split_expense_rule",
    "evaluate_supplier_concentration_rule",
    "evaluate_temporal_geographic_overlap_rule",
    "evaluate_weekend_holiday_expense_rule",
    "extract_cnpj_root",
    "get_brazilian_national_holidays",
    "is_parliamentary_recess",
    "is_weekend_or_holiday",
]


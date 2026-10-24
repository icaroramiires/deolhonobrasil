"""Modelos de dados, contratos de proveniência e taxonomia epistêmica do pipeline.

Implementa as exigências das Seções 7.6, 8, 10 e 12.1:
- Rastreabilidade 100%: nenhum registro existe na camada Curated sem ProvenanceMetadata.
- Taxonomia Epistêmica obrigatória: diferenciação estrita entre fato documentado,
  divergência entre bases, sinal estatístico e hipótese em revisão.
- Vedação a linguagem acusatória automática.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from deolhonobrasil.pipeline.privacy import (
    compute_sha256_text,
    normalize_and_protect_document,
    parse_strict_monetary_value,
    sanitize_untrusted_text,
)


class OfficialSource(StrEnum):
    """Fontes primárias oficiais integradas no MVP."""

    CAMARA_CEAP = "CAMARA_CEAP"
    SENADO_CEAPS = "SENADO_CEAPS"
    CGU_EMENDAS = "CGU_EMENDAS"
    CGU_CEIS_CNEP = "CGU_CEIS_CNEP"
    PNCP_CONTRATOS = "PNCP_CONTRATOS"
    RFB_CNPJ = "RFB_CNPJ"
    IBGE_LOCALIDADES = "IBGE_LOCALIDADES"


class EpistemicClassification(StrEnum):
    """Taxonomia epistêmica obrigatória (Seções 7.6 e 12.1)."""

    DOCUMENTED_FACT = "FATO_DIRETO_DOCUMENTADO"
    CROSS_SOURCE_DIVERGENCE = "DIVERGENCIA_ENTRE_REGISTROS"
    STATISTICAL_ANOMALY = "ANOMALIA_ESTATISTICA_PARA_REVISAO"
    UNVALIDATED_HYPOTHESIS = "INDICIO_PENDENTE_DE_VALIDACAO"
    CONTESTED_UNDER_REVIEW = "INFORMACAO_CONTESTADA_EM_REVISAO"
    REVIEWED_BY_SPECIALIST = "CONCLUSAO_REVISADA_POR_HUMANO"
    OFFICIAL_AUDIT_FINDING = "RESULTADO_DE_AUDITORIA_OFICIAL"


FORBIDDEN_ACCUSATORY_TERMS: tuple[str, ...] = (
    "fraude comprovada",
    "corrupção comprovada",
    "roubo",
    "criminoso",
    "superfaturamento comprovado",
    "desvio criminoso",
    "culpado",
)


def assert_non_accusatory_language(text: str) -> None:
    """Garante que nenhum texto gerado por regra ou conector use linguagem acusatória (Seção 12.1)."""
    lowered = (text or "").lower()
    for term in FORBIDDEN_ACCUSATORY_TERMS:
        if term in lowered:
            raise ValueError(
                f"Violação da Política Editorial (Seção 12.1): o termo acusatório '{term}' "
                "é estritamente proibido sem decisão institucional transitada em julgado."
            )


@dataclass(frozen=True, slots=True)
class ProvenanceMetadata:
    """Metadados obrigatórios de proveniência e cadeia de custódia digital."""

    source: OfficialSource
    source_url: str
    source_record_id: str
    collected_at_utc: str
    raw_batch_sha256: str
    schema_version: str = "1.0.0"
    extraction_method: str = "deterministic_structured_parser"
    extraction_confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_url.startswith(("https://", "http://")):
            raise ValueError(f"source_url deve ser uma URL válida: '{self.source_url}'")
        if not self.source_record_id.strip():
            raise ValueError("source_record_id é obrigatório para rastreabilidade ao registro original.")
        if len(self.raw_batch_sha256) != 64:
            raise ValueError(f"raw_batch_sha256 inválido (esperado 64 hex chars): '{self.raw_batch_sha256}'")
        if not (0.0 <= self.extraction_confidence <= 1.0):
            raise ValueError("extraction_confidence deve estar entre 0.0 e 1.0.")


@dataclass(frozen=True, slots=True)
class CuratedPublicExpense:
    """Registro padronizado e validado de despesa pública (CEAP, CEAPS ou Execução)."""

    natural_key: str
    competence_year: int
    competence_month: int
    issue_date: date
    sphere: str
    organ_code: str
    organ_name: str
    public_agent_id: str
    public_agent_name: str
    party_sigla: str
    state_uf: str
    expense_category: str
    supplier_doc_normalized: str
    supplier_doc_type: str
    supplier_name: str
    document_number: str
    gross_amount: Decimal
    net_amount: Decimal
    document_evidence_url: str | None
    provenance: ProvenanceMetadata
    epistemic_status: EpistemicClassification = EpistemicClassification.DOCUMENTED_FACT

    @classmethod
    def create_validated(
        cls,
        *,
        competence_year: int,
        competence_month: int,
        issue_date: date,
        sphere: str,
        organ_code: str,
        organ_name: str,
        public_agent_id: str,
        public_agent_name: str,
        party_sigla: str,
        state_uf: str,
        expense_category: str,
        supplier_raw_doc: str,
        supplier_name: str,
        document_number: str,
        gross_amount_raw: str | int | float | Decimal | None,
        net_amount_raw: str | int | float | Decimal | None,
        document_evidence_url: str | None,
        provenance: ProvenanceMetadata,
    ) -> CuratedPublicExpense:
        """Fábrica determinística que valida schema, LGPD e valores monetários."""
        if not (2000 <= int(competence_year) <= 2100):
            raise ValueError(f"Ano de competência fora do intervalo válido: {competence_year}")
        if not (1 <= int(competence_month) <= 12):
            raise ValueError(f"Mês de competência inválido: {competence_month}")

        doc_norm, doc_type = normalize_and_protect_document(supplier_raw_doc)
        gross_val = parse_strict_monetary_value(gross_amount_raw, "gross_amount")
        net_val = parse_strict_monetary_value(net_amount_raw, "net_amount")

        if net_val <= Decimal("0.00"):
            raise ValueError(
                f"Valor líquido deve ser estritamente positivo para despesa ordinária (recebido: {net_val})."
            )

        clean_category = sanitize_untrusted_text(expense_category, max_length=250)
        clean_supplier = sanitize_untrusted_text(supplier_name, max_length=250)
        clean_agent = sanitize_untrusted_text(public_agent_name, max_length=200)
        clean_doc_num = sanitize_untrusted_text(document_number, max_length=100)

        if not clean_category or not clean_supplier:
            raise ValueError("Categoria da despesa e nome do favorecido são obrigatórios.")

        # Chave natural determinística para idempotência e desduplicação
        composite_seed = (
            f"{provenance.source.value}|{provenance.source_record_id}|"
            f"{competence_year}|{competence_month}|{doc_norm}|{clean_doc_num}|{net_val}"
        )
        natural_key = compute_sha256_text(composite_seed)

        return cls(
            natural_key=natural_key,
            competence_year=int(competence_year),
            competence_month=int(competence_month),
            issue_date=issue_date,
            sphere=sanitize_untrusted_text(sphere, 50),
            organ_code=sanitize_untrusted_text(organ_code, 50),
            organ_name=sanitize_untrusted_text(organ_name, 150),
            public_agent_id=sanitize_untrusted_text(public_agent_id, 60),
            public_agent_name=clean_agent,
            party_sigla=sanitize_untrusted_text(party_sigla, 30) or "N/A",
            state_uf=sanitize_untrusted_text(state_uf, 2).upper() or "BR",
            expense_category=clean_category,
            supplier_doc_normalized=doc_norm,
            supplier_doc_type=doc_type,
            supplier_name=clean_supplier,
            document_number=clean_doc_num,
            gross_amount=gross_val,
            net_amount=net_val,
            document_evidence_url=(
                sanitize_untrusted_text(document_evidence_url, 500) if document_evidence_url else None
            ),
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class CuratedPublicContract:
    """Registro padronizado de contrato público federal (PNCP / CGU - Lei 14.133/2021)."""

    natural_key: str
    pncp_control_number: str
    organ_cnpj: str
    organ_name: str
    supplier_doc_normalized: str
    supplier_doc_type: str
    supplier_name: str
    modality_name: str
    contract_object: str
    signature_date: date
    initial_amount: Decimal
    current_amount: Decimal
    addendum_count: int
    provenance: ProvenanceMetadata

    @classmethod
    def create_validated(
        cls,
        *,
        pncp_control_number: str,
        organ_cnpj_raw: str,
        organ_name: str,
        supplier_raw_doc: str,
        supplier_name: str,
        modality_name: str,
        contract_object: str,
        signature_date: date,
        initial_amount_raw: str | int | float | Decimal | None,
        current_amount_raw: str | int | float | Decimal | None,
        addendum_count: int,
        provenance: ProvenanceMetadata,
    ) -> CuratedPublicContract:
        organ_cnpj, organ_type = normalize_and_protect_document(organ_cnpj_raw)
        if organ_type != "CNPJ":
            raise ValueError(f"Órgão público deve possuir CNPJ válido de 14 dígitos: {organ_cnpj_raw}")

        sup_doc, sup_type = normalize_and_protect_document(supplier_raw_doc)
        initial_val = parse_strict_monetary_value(initial_amount_raw, "initial_amount")
        current_val = parse_strict_monetary_value(current_amount_raw, "current_amount")

        if initial_val <= Decimal("0.00") or current_val <= Decimal("0.00"):
            raise ValueError("Valores inicial e atual do contrato devem ser maiores que zero.")
        if addendum_count < 0:
            raise ValueError("Número de termos aditivos não pode ser negativo.")

        clean_control = sanitize_untrusted_text(pncp_control_number, 80)
        if not clean_control:
            raise ValueError("Número de controle PNCP é obrigatório.")

        natural_key = compute_sha256_text(f"{provenance.source.value}|{clean_control}|{sup_doc}")

        return cls(
            natural_key=natural_key,
            pncp_control_number=clean_control,
            organ_cnpj=organ_cnpj,
            organ_name=sanitize_untrusted_text(organ_name, 200),
            supplier_doc_normalized=sup_doc,
            supplier_doc_type=sup_type,
            supplier_name=sanitize_untrusted_text(supplier_name, 250),
            modality_name=sanitize_untrusted_text(modality_name, 120),
            contract_object=sanitize_untrusted_text(contract_object, 1000),
            signature_date=signature_date,
            initial_amount=initial_val,
            current_amount=current_val,
            addendum_count=int(addendum_count),
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class CuratedParliamentaryAmendment:
    """Registro padronizado de Emenda Parlamentar (Portal da Transparência / CGU)."""

    natural_key: str
    amendment_code: str
    year: int
    author_id: str
    author_name: str
    amendment_type: str
    function_name: str
    municipality_ibge_code: str
    state_uf: str
    beneficiary_doc_normalized: str
    beneficiary_name: str
    committed_amount: Decimal
    paid_amount: Decimal
    provenance: ProvenanceMetadata

    @classmethod
    def create_validated(
        cls,
        *,
        amendment_code: str,
        year: int,
        author_id: str,
        author_name: str,
        amendment_type: str,
        function_name: str,
        municipality_ibge_code: str,
        state_uf: str,
        beneficiary_raw_doc: str,
        beneficiary_name: str,
        committed_amount_raw: str | int | float | Decimal | None,
        paid_amount_raw: str | int | float | Decimal | None,
        provenance: ProvenanceMetadata,
    ) -> CuratedParliamentaryAmendment:
        ibge_clean = sanitize_untrusted_text(municipality_ibge_code, 10)
        if ibge_clean != "NACIONAL" and (not ibge_clean.isdigit() or len(ibge_clean) != 7):
            raise ValueError(
                f"Código IBGE de município inválido (deve ter 7 dígitos ou 'NACIONAL'): '{municipality_ibge_code}'"
            )

        ben_doc, _ = normalize_and_protect_document(beneficiary_raw_doc)
        committed_val = parse_strict_monetary_value(committed_amount_raw, "committed_amount")
        paid_val = parse_strict_monetary_value(paid_amount_raw, "paid_amount")

        if committed_val < Decimal("0.00") or paid_val < Decimal("0.00"):
            raise ValueError("Valores empenhado e pago de emenda não podem ser negativos.")

        clean_code = sanitize_untrusted_text(amendment_code, 50)
        if not clean_code:
            raise ValueError("Código da emenda parlamentar é obrigatório.")

        natural_key = compute_sha256_text(
            f"{provenance.source.value}|{clean_code}|{year}|{ibge_clean}|{ben_doc}"
        )

        return cls(
            natural_key=natural_key,
            amendment_code=clean_code,
            year=int(year),
            author_id=sanitize_untrusted_text(author_id, 60),
            author_name=sanitize_untrusted_text(author_name, 200),
            amendment_type=sanitize_untrusted_text(amendment_type, 120),
            function_name=sanitize_untrusted_text(function_name, 120),
            municipality_ibge_code=ibge_clean,
            state_uf=sanitize_untrusted_text(state_uf, 2).upper(),
            beneficiary_doc_normalized=ben_doc,
            beneficiary_name=sanitize_untrusted_text(beneficiary_name, 250),
            committed_amount=committed_val,
            paid_amount=paid_val,
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class QuarantinedRecord:
    """Registro isolado em quarentena por falha de validação de schema ou integridade (Seção 8)."""

    quarantine_id: str
    source: OfficialSource
    source_record_id: str
    raw_batch_sha256: str
    rejection_reason: str
    raw_payload_json: str
    quarantined_at_utc: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

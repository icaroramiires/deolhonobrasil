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
    RECEITA_FEDERAL_CNPJ = "RECEITA_FEDERAL_CNPJ"
    IBGE_LOCALIDADES = "IBGE_LOCALIDADES"
    TSE_ELEICOES = "TSE_ELEICOES"


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
class CuratedSanctionRecord:
    """Registro padronizado de sanção administrativa vigente (CEIS/CNEP - CGU / `SPEC-0007`)."""

    natural_key: str
    sanction_code: str
    sanctioned_doc_normalized: str
    sanctioned_doc_type: str
    sanctioned_name: str
    sanction_type: str
    sanctioning_organ: str
    state_uf: str
    start_date: date
    end_date: date | None
    provenance: ProvenanceMetadata

    @classmethod
    def create_validated(
        cls,
        *,
        sanction_code: str,
        sanctioned_raw_doc: str,
        sanctioned_name: str,
        sanction_type: str,
        sanctioning_organ: str,
        state_uf: str,
        start_date: date,
        end_date: date | None,
        provenance: ProvenanceMetadata,
    ) -> CuratedSanctionRecord:
        clean_code = sanitize_untrusted_text(sanction_code, 80)
        if not clean_code:
            raise ValueError("Código da sanção (sanction_code) é obrigatório.")

        doc_norm, doc_type = normalize_and_protect_document(sanctioned_raw_doc)
        clean_name = sanitize_untrusted_text(sanctioned_name, 250)
        clean_type = sanitize_untrusted_text(sanction_type, 200)
        clean_organ = sanitize_untrusted_text(sanctioning_organ, 200)
        if not clean_name or not clean_type:
            raise ValueError("Nome do sancionado e tipo de sanção são obrigatórios.")

        if end_date is not None and end_date < start_date:
            raise ValueError("Data final da sanção não pode ser anterior à data inicial.")

        natural_key = compute_sha256_text(
            f"{provenance.source.value}|{clean_code}|{doc_norm}|{start_date.isoformat()}"
        )
        return cls(
            natural_key=natural_key,
            sanction_code=clean_code,
            sanctioned_doc_normalized=doc_norm,
            sanctioned_doc_type=doc_type,
            sanctioned_name=clean_name,
            sanction_type=clean_type,
            sanctioning_organ=clean_organ or "N/A",
            state_uf=sanitize_untrusted_text(state_uf, 2).upper() or "BR",
            start_date=start_date,
            end_date=end_date,
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class CuratedElectoralDonation:
    """Registro padronizado de doação eleitoral declarada (TSE / `SPEC-0012`)."""

    natural_key: str
    election_year: int
    candidate_id: str
    candidate_name: str
    candidate_office: str
    donor_doc_normalized: str
    donor_doc_type: str
    donor_name: str
    donation_amount: Decimal
    donation_date: date | None
    receipt_number: str
    provenance: ProvenanceMetadata

    @classmethod
    def create_validated(
        cls,
        *,
        election_year: int,
        candidate_id: str,
        candidate_name: str,
        candidate_office: str,
        donor_raw_doc: str,
        donor_name: str,
        donation_amount_raw: str | Decimal,
        donation_date: date | None,
        receipt_number: str,
        provenance: ProvenanceMetadata,
    ) -> CuratedElectoralDonation:
        clean_cand_id = sanitize_untrusted_text(candidate_id, 50)
        clean_cand_name = sanitize_untrusted_text(candidate_name, 200)
        clean_office = sanitize_untrusted_text(candidate_office, 100)
        clean_receipt = sanitize_untrusted_text(receipt_number, 80)
        clean_donor_name = sanitize_untrusted_text(donor_name, 250)

        if not clean_cand_id or not clean_cand_name:
            raise ValueError("Identificador e nome do candidato são obrigatórios.")
        if not clean_receipt:
            raise ValueError("Número do recibo eleitoral é obrigatório.")

        doc_norm, doc_type = normalize_and_protect_document(donor_raw_doc)
        parsed_amount = parse_strict_monetary_value(donation_amount_raw, "donation_amount")
        if parsed_amount <= Decimal("0"):
            raise ValueError("Valor da doação deve ser estritamente positivo.")

        natural_key = compute_sha256_text(
            f"{provenance.source.value}|{election_year}|{clean_cand_id}|{clean_receipt}|{doc_norm}"
        )

        return cls(
            natural_key=natural_key,
            election_year=int(election_year),
            candidate_id=clean_cand_id,
            candidate_name=clean_cand_name,
            candidate_office=clean_office or "N/A",
            donor_doc_normalized=doc_norm,
            donor_doc_type=doc_type,
            donor_name=clean_donor_name or "DOADOR NÃO IDENTIFICADO",
            donation_amount=parsed_amount,
            donation_date=donation_date,
            receipt_number=clean_receipt,
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class CuratedCorporateMemberRecord:
    """Quadro de Sócios e Administradores (QSA) da Receita Federal (SPEC-0013 / FR-028 / DATA-015)."""

    corporate_root_cnpj: str
    full_cnpj_normalized: str
    member_name_raw: str
    member_doc_masked: str
    qualification_code: str
    qualification_description: str
    entry_date: date | str | None
    provenance: ProvenanceMetadata
    natural_key: str = field(default="")

    def __post_init__(self) -> None:
        clean_root = (self.corporate_root_cnpj or "").strip().replace(".", "").replace("/", "").replace("-", "")
        if not clean_root or len(clean_root) != 8 or not clean_root.isdigit():
            raise ValueError(f"corporate_root_cnpj deve conter exatamente 8 dígitos numéricos: '{self.corporate_root_cnpj}'")
        clean_name = sanitize_untrusted_text(self.member_name_raw, 250)
        if not clean_name:
            raise ValueError("member_name_raw é obrigatório.")
        clean_doc = sanitize_untrusted_text(self.member_doc_masked, 50)
        if not clean_doc:
            raise ValueError("member_doc_masked é obrigatório.")
        clean_qual = sanitize_untrusted_text(self.qualification_description, 100) or "Sócio"
        object.__setattr__(self, "corporate_root_cnpj", clean_root)
        object.__setattr__(self, "member_name_raw", clean_name)
        object.__setattr__(self, "member_doc_masked", clean_doc)
        object.__setattr__(self, "qualification_description", clean_qual)
        if not self.natural_key:
            nk = compute_sha256_text(
                f"{self.provenance.source.value}|{clean_root}|{clean_doc}|{clean_name}"
            )
            object.__setattr__(self, "natural_key", nk)


@dataclass(frozen=True, slots=True)
class CuratedCompanyRegistrationRecord:
    """Cadastro formal de Pessoa Jurídica na Receita Federal (RFB CNPJ) (SPEC-0014)."""

    cnpj_normalized: str
    corporate_root_cnpj: str
    legal_name: str
    trade_name: str | None
    opening_date: date
    share_capital_brl: Decimal
    cnae_main_code: str
    registration_status: str
    provenance: ProvenanceMetadata
    natural_key: str = field(default="")

    def __post_init__(self) -> None:
        digits = "".join(ch for ch in str(self.cnpj_normalized) if ch.isdigit())
        if len(digits) != 14:
            raise ValueError(f"CNPJ deve conter 14 dígitos numéricos: '{self.cnpj_normalized}'")
        clean_root = (self.corporate_root_cnpj or digits[:8]).strip()
        if len(clean_root) != 8 or not clean_root.isdigit():
            clean_root = digits[:8]
        clean_legal = sanitize_untrusted_text(self.legal_name, 250)
        if not clean_legal:
            raise ValueError("legal_name (razão social) é obrigatório.")
        clean_trade = sanitize_untrusted_text(self.trade_name, 250) if self.trade_name else None
        clean_cnae = sanitize_untrusted_text(self.cnae_main_code, 20) or "0000-0/00"
        clean_status = sanitize_untrusted_text(self.registration_status, 50) or "ATIVA"
        capital = Decimal(str(self.share_capital_brl))
        if capital < Decimal("0.00"):
            raise ValueError("Capital social não pode ser negativo.")

        object.__setattr__(self, "cnpj_normalized", digits)
        object.__setattr__(self, "corporate_root_cnpj", clean_root)
        object.__setattr__(self, "legal_name", clean_legal)
        object.__setattr__(self, "trade_name", clean_trade)
        object.__setattr__(self, "share_capital_brl", capital)
        object.__setattr__(self, "cnae_main_code", clean_cnae)
        object.__setattr__(self, "registration_status", clean_status)

        if not self.natural_key:
            nk = compute_sha256_text(
                f"{self.provenance.source.value}|{digits}|{self.opening_date.isoformat()}|{capital:.2f}"
            )
            object.__setattr__(self, "natural_key", nk)

    @classmethod
    def create_validated(
        cls,
        cnpj_raw: str,
        legal_name: str,
        opening_date: date,
        share_capital_raw: str | int | float | Decimal,
        provenance: ProvenanceMetadata,
        trade_name: str | None = None,
        cnae_main_code: str = "0000-0/00",
        registration_status: str = "ATIVA",
    ) -> CuratedCompanyRegistrationRecord:
        doc_norm, doc_type = normalize_and_protect_document(cnpj_raw)
        if doc_type != "CNPJ":
            raise ValueError(f"Documento informado não é um CNPJ válido de 14 dígitos: {cnpj_raw}")
        capital = parse_strict_monetary_value(share_capital_raw, "share_capital_brl")
        return cls(
            cnpj_normalized=doc_norm,
            corporate_root_cnpj=doc_norm[:8],
            legal_name=legal_name,
            trade_name=trade_name,
            opening_date=opening_date,
            share_capital_brl=capital,
            cnae_main_code=cnae_main_code,
            registration_status=registration_status,
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


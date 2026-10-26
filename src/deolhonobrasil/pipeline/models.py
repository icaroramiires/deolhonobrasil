"""Modelos de dados, contratos de proveniência e taxonomia epistêmica do pipeline.

Implementa as exigências das Seções 7.6, 8, 10 e 12.1:
- Rastreabilidade 100%: nenhum registro existe na camada Curated sem ProvenanceMetadata.
- Taxonomia Epistêmica obrigatória: diferenciação estrita entre fato documentado,
  divergência entre bases, sinal estatístico e hipótese em revisão.
- Vedação a linguagem acusatória automática.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import re
import unicodedata

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
    PORTAL_TRANSPARENCIA_SERVIDORES = "PORTAL_TRANSPARENCIA_SERVIDORES"


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


def normalize_cnae_code(raw: str) -> str:
    """Normaliza código CNAE para 7 dígitos numéricos estritos (ex: '42.11-1-01' -> '4211101')."""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) != 7:
        raise ValueError(f"Código CNAE deve conter exatamente 7 dígitos numéricos: '{raw}'")
    return digits


def normalize_postal_code(raw: str) -> str:
    """Normaliza CEP brasileiro para 8 dígitos numéricos estritos (ex: '70000-000' -> '70000000') (SPEC-0017)."""
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(digits) == 8:
        return digits
    if not digits or digits == "00000000":
        return "00000000"
    if 1 <= len(digits) < 8:
        return digits.zfill(8)
    raise ValueError(f"CEP deve conter exatamente 8 dígitos numéricos: '{raw}'")


def normalize_street_address(raw: str) -> str:
    """Normaliza logradouro removendo acentuação, padronizando prefixos e pontuação (SPEC-0017 / NFR-020)."""
    text = unicodedata.normalize("NFKD", str(raw or "")).encode("ASCII", "ignore").decode("ASCII").upper()
    text = re.sub(r"\b(N|NO|NUM|NUMERO)\b\.?", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()
    if not words:
        return "N/A"

    prefix_map = {
        "R": "RUA",
        "RUA": "RUA",
        "AV": "AVENIDA",
        "AVENIDA": "AVENIDA",
        "AL": "ALAMEDA",
        "ALAMEDA": "ALAMEDA",
        "ROD": "RODOVIA",
        "RODOVIA": "RODOVIA",
        "PC": "PRACA",
        "PCA": "PRACA",
        "PRACA": "PRACA",
        "TV": "TRAVESSA",
        "TRAVESSA": "TRAVESSA",
        "QD": "QUADRA",
        "QDA": "QUADRA",
        "QUADRA": "QUADRA",
        "LT": "LOTE",
        "LTE": "LOTE",
        "LOTE": "LOTE",
        "ST": "SETOR",
        "STR": "SETOR",
        "SETOR": "SETOR",
    }
    if words[0] in prefix_map:
        words[0] = prefix_map[words[0]]
    return " ".join(words)


def normalize_address_number(raw: str) -> str:
    """Normaliza número predial (ex: 'S/N', 'SN', '0', 's/n' -> 'SN'; '123' -> '123') (SPEC-0017)."""
    text = unicodedata.normalize("NFKD", str(raw or "")).encode("ASCII", "ignore").decode("ASCII").upper().strip()
    clean = re.sub(r"[^\w]", "", text)
    if not clean or clean in ("SN", "0", "SEMNUMERO"):
        return "SN"
    return clean


def extract_autonomous_unit(raw_complement: str | None) -> str | None:
    """Extrai identificador de unidade autônoma (sala, loja, conjunto, andar, box, apto, galpão) (SPEC-0017)."""
    if not raw_complement:
        return None
    text = unicodedata.normalize("NFKD", str(raw_complement)).encode("ASCII", "ignore").decode("ASCII").upper().strip()
    if not text or text in ("N/A", "NA", "NENHUM", "NULL", "NONE", "SN", "SEM COMPLEMENTO"):
        return None
    text = re.sub(r"[^\w\s]", " ", text)
    cleaned = " ".join(text.split())
    if not cleaned or cleaned in ("N A", "NA", "NENHUM", "NULL", "NONE", "SN", "SEM COMPLEMENTO"):
        return None
    match = re.search(
        r"\b(SALA|SL|LOJA|LJ|CONJUNTO|CJ|ANDAR|PAVIMENTO|BOX|APARTAMENTO|APTO|BLOCO|GALPAO)\s*([A-Z0-9\-]+)",
        cleaned,
    )
    if match:
        unit_type = match.group(1)
        unit_num = match.group(2)
        type_norm = {
            "SALA": "SALA",
            "SL": "SALA",
            "LOJA": "LOJA",
            "LJ": "LOJA",
            "CONJUNTO": "CJ",
            "CJ": "CJ",
            "ANDAR": "ANDAR",
            "PAVIMENTO": "ANDAR",
            "BOX": "BOX",
            "APARTAMENTO": "APTO",
            "APTO": "APTO",
            "BLOCO": "BLOCO",
            "GALPAO": "GALPAO",
        }.get(unit_type, unit_type)
        return f"{type_norm} {unit_num}"
    return cleaned


def compute_normalized_address_key(
    postal_code: str,
    street_address: str,
    address_number: str,
    complement: str | None = None,
) -> str:
    """Calcula hash determinístico SHA-256 da chave canônica de endereço físico (SPEC-0017 / DATA-019)."""
    norm_cep = normalize_postal_code(postal_code)
    norm_street = normalize_street_address(street_address)
    norm_number = normalize_address_number(address_number)
    unit = extract_autonomous_unit(complement)
    unit_str = f"|{unit}" if unit else ""
    raw_key = f"{norm_cep}|{norm_street}|{norm_number}{unit_str}"
    return compute_sha256_text(raw_key)


@dataclass(frozen=True, slots=True)
class CuratedCompanyRegistrationRecord:
    """Cadastro formal de Pessoa Jurídica na Receita Federal (RFB CNPJ) (SPEC-0014 / SPEC-0015 / SPEC-0017)."""

    cnpj_normalized: str
    corporate_root_cnpj: str
    legal_name: str
    trade_name: str | None
    opening_date: date
    share_capital_brl: Decimal
    cnae_main_code: str
    registration_status: str
    provenance: ProvenanceMetadata
    secondary_cnae_codes: tuple[str, ...] = field(default_factory=tuple)
    postal_code: str = "00000000"
    street_address: str = "N/A"
    address_number: str = "S/N"
    address_complement: str | None = None
    district: str = "CENTRO"
    city: str = "BRASILIA"
    state_uf: str = "DF"
    natural_key: str = field(default="")

    @property
    def main_cnae_code(self) -> str:
        """Alias padronizado para cnae_main_code (SPEC-0015)."""
        return self.cnae_main_code

    @property
    def normalized_address_key(self) -> str:
        """Chave determinística de endereço físico com unidade autônoma se houver (SPEC-0017)."""
        return compute_normalized_address_key(
            self.postal_code,
            self.street_address,
            self.address_number,
            self.address_complement,
        )

    @property
    def base_building_address_key(self) -> str:
        """Chave determinística da edificação física sem unidade autônoma (SPEC-0017)."""
        return compute_normalized_address_key(
            self.postal_code,
            self.street_address,
            self.address_number,
            None,
        )

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

        digits_cnae = "".join(ch for ch in str(self.cnae_main_code) if ch.isdigit())
        if len(digits_cnae) == 7:
            clean_cnae = digits_cnae
        elif not digits_cnae or digits_cnae == "0000000" or self.cnae_main_code == "0000-0/00":
            clean_cnae = "0000000"
        else:
            raise ValueError(f"Código CNAE principal deve conter 7 dígitos numéricos: '{self.cnae_main_code}'")

        clean_secondaries: list[str] = []
        for sec in self.secondary_cnae_codes:
            sec_digits = "".join(ch for ch in str(sec) if ch.isdigit())
            if len(sec_digits) != 7:
                raise ValueError(f"Código CNAE secundário deve conter 7 dígitos numéricos: '{sec}'")
            clean_secondaries.append(sec_digits)

        clean_status = sanitize_untrusted_text(self.registration_status, 50) or "ATIVA"
        capital = Decimal(str(self.share_capital_brl))
        if capital < Decimal("0.00"):
            raise ValueError("Capital social não pode ser negativo.")

        # Normalização de endereço físico (SPEC-0017)
        clean_cep = normalize_postal_code(self.postal_code) if self.postal_code else "00000000"
        clean_street = sanitize_untrusted_text(self.street_address, 200) or "N/A"
        clean_number = sanitize_untrusted_text(self.address_number, 50) or "S/N"
        clean_comp = sanitize_untrusted_text(self.address_complement, 100) if self.address_complement else None
        clean_district = sanitize_untrusted_text(self.district, 100) or "CENTRO"
        clean_city = sanitize_untrusted_text(self.city, 100) or "BRASILIA"
        clean_uf = (sanitize_untrusted_text(self.state_uf, 2) or "DF").upper()

        object.__setattr__(self, "cnpj_normalized", digits)
        object.__setattr__(self, "corporate_root_cnpj", clean_root)
        object.__setattr__(self, "legal_name", clean_legal)
        object.__setattr__(self, "trade_name", clean_trade)
        object.__setattr__(self, "share_capital_brl", capital)
        object.__setattr__(self, "cnae_main_code", clean_cnae)
        object.__setattr__(self, "registration_status", clean_status)
        object.__setattr__(self, "secondary_cnae_codes", tuple(clean_secondaries))
        object.__setattr__(self, "postal_code", clean_cep)
        object.__setattr__(self, "street_address", clean_street)
        object.__setattr__(self, "address_number", clean_number)
        object.__setattr__(self, "address_complement", clean_comp)
        object.__setattr__(self, "district", clean_district)
        object.__setattr__(self, "city", clean_city)
        object.__setattr__(self, "state_uf", clean_uf)

        if not self.natural_key:
            secondaries_str = "|".join(clean_secondaries)
            nk = compute_sha256_text(
                f"{self.provenance.source.value}|{digits}|{self.opening_date.isoformat()}|{capital:.2f}|{clean_cnae}|{secondaries_str}"
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
        cnae_main_code: str = "0000000",
        registration_status: str = "ATIVA",
        secondary_cnae_codes: Sequence[str] = (),
        postal_code: str = "00000000",
        street_address: str = "N/A",
        address_number: str = "S/N",
        address_complement: str | None = None,
        district: str = "CENTRO",
        city: str = "BRASILIA",
        state_uf: str = "DF",
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
            secondary_cnae_codes=tuple(secondary_cnae_codes),
            postal_code=postal_code,
            street_address=street_address,
            address_number=address_number,
            address_complement=address_complement,
            district=district,
            city=city,
            state_uf=state_uf,
        )


@dataclass(frozen=True, slots=True)
class CuratedPublicAgentRecord:
    """Registro padronizado de agente público / servidor público (SPEC-0016 / FR-034 / DATA-018)."""

    agent_id: str
    organ_code: str
    organ_name: str
    agent_name: str
    agent_doc_masked: str
    position_title: str
    status: str
    provenance: ProvenanceMetadata
    natural_key: str = field(default="")

    def __post_init__(self) -> None:
        clean_agent_id = sanitize_untrusted_text(self.agent_id, 80)
        if not clean_agent_id:
            raise ValueError("agent_id é obrigatório.")
        clean_organ_code = sanitize_untrusted_text(self.organ_code, 50)
        if not clean_organ_code:
            raise ValueError("organ_code é obrigatório.")
        clean_organ_name = sanitize_untrusted_text(self.organ_name, 200)
        if not clean_organ_name:
            raise ValueError("organ_name é obrigatório.")
        clean_name = sanitize_untrusted_text(self.agent_name, 250)
        if not clean_name:
            raise ValueError("agent_name é obrigatório.")
        clean_doc = sanitize_untrusted_text(self.agent_doc_masked, 50)
        if not clean_doc:
            raise ValueError("agent_doc_masked é obrigatório.")
        clean_pos = sanitize_untrusted_text(self.position_title, 150) or "Agente Público"
        clean_status = sanitize_untrusted_text(self.status, 50) or "ATIVO"

        object.__setattr__(self, "agent_id", clean_agent_id)
        object.__setattr__(self, "organ_code", clean_organ_code)
        object.__setattr__(self, "organ_name", clean_organ_name)
        object.__setattr__(self, "agent_name", clean_name)
        object.__setattr__(self, "agent_doc_masked", clean_doc)
        object.__setattr__(self, "position_title", clean_pos)
        object.__setattr__(self, "status", clean_status)

        if not self.natural_key:
            nk = compute_sha256_text(
                f"{self.provenance.source.value}|{clean_organ_code}|{clean_agent_id}|{clean_doc}|{clean_name}"
            )
            object.__setattr__(self, "natural_key", nk)

    @classmethod
    def create_validated(
        cls,
        *,
        agent_id: str,
        organ_code: str,
        organ_name: str,
        agent_name: str,
        agent_doc_raw: str | None = None,
        agent_doc_masked: str | None = None,
        position_title: str = "Agente Público",
        provenance: ProvenanceMetadata,
        status: str = "ATIVO",
    ) -> CuratedPublicAgentRecord:
        raw_doc = (agent_doc_raw or agent_doc_masked or "").strip()
        if not raw_doc:
            raise ValueError("Documento de identificação do agente público é obrigatório.")
        doc_norm, doc_type = normalize_and_protect_document(raw_doc)
        if doc_type != "CPF_MASKED":
            raise ValueError(f"Documento do agente público deve ser um CPF válido ou já mascarado: {raw_doc}")
        return cls(
            agent_id=agent_id,
            organ_code=organ_code,
            organ_name=organ_name,
            agent_name=agent_name,
            agent_doc_masked=doc_norm,
            position_title=position_title,
            status=status,
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


@dataclass(frozen=True, slots=True)
class ContractTimelineEvent:
    """Evento cronológico na linha do tempo de um contrato público (SPEC-0020 / FR-044)."""

    event_id: str
    contract_id: str
    event_type: str  # e.g., 'CONTRATO_ORIGINAL', 'TERMO_ADITIVO_VALOR', 'TERMO_ADITIVO_VIGENCIA', 'TERMO_ADITIVO_MISTO'
    event_date: str
    description: str
    value_delta_brl: Decimal
    new_total_brl: Decimal
    provenance_sha256: str

    def __post_init__(self) -> None:
        clean_event_id = sanitize_untrusted_text(self.event_id, 80)
        if not clean_event_id:
            raise ValueError("event_id é obrigatório.")
        clean_contract_id = sanitize_untrusted_text(self.contract_id, 80)
        if not clean_contract_id:
            raise ValueError("contract_id é obrigatório.")
        clean_type = sanitize_untrusted_text(self.event_type, 60) or "CONTRATO_ORIGINAL"
        clean_date = sanitize_untrusted_text(self.event_date, 30)
        if not clean_date:
            raise ValueError("event_date é obrigatório.")
        clean_desc = sanitize_untrusted_text(self.description, 500) or "Registro de execução contratual"
        clean_prov = sanitize_untrusted_text(self.provenance_sha256, 64)
        if len(clean_prov) != 64:
            raise ValueError("provenance_sha256 deve ser um hash hexadecimal de 64 caracteres.")

        object.__setattr__(self, "event_id", clean_event_id)
        object.__setattr__(self, "contract_id", clean_contract_id)
        object.__setattr__(self, "event_type", clean_type)
        object.__setattr__(self, "event_date", clean_date)
        object.__setattr__(self, "description", clean_desc)
        object.__setattr__(self, "provenance_sha256", clean_prov)
        object.__setattr__(self, "value_delta_brl", Decimal(str(self.value_delta_brl)).quantize(Decimal("0.01")))
        object.__setattr__(self, "new_total_brl", Decimal(str(self.new_total_brl)).quantize(Decimal("0.01")))


@dataclass(frozen=True, slots=True)
class ExpenseDetailPayload:
    """Detalhamento analítico de despesa com os 3 estágios contábeis (SPEC-0020 / FR-044)."""

    expense_id: str
    public_agent_id: str
    public_agent_name: str
    supplier_name: str
    supplier_doc: str
    organ_name: str
    issue_date: str
    document_number: str
    subquota_description: str
    committed_amount_brl: Decimal
    liquidated_amount_brl: Decimal
    paid_amount_brl: Decimal
    is_reconciled: bool
    provenance_sha256: str
    official_source_url: str

    def __post_init__(self) -> None:
        clean_id = sanitize_untrusted_text(self.expense_id, 80)
        if not clean_id:
            raise ValueError("expense_id é obrigatório.")
        clean_agent_id = sanitize_untrusted_text(self.public_agent_id, 80) or "N/D"
        clean_agent_name = sanitize_untrusted_text(self.public_agent_name, 250) or "Agente Público"
        clean_supplier_name = sanitize_untrusted_text(self.supplier_name, 250) or "Fornecedor"
        clean_supplier_doc = sanitize_untrusted_text(self.supplier_doc, 50) or "N/D"
        clean_organ = sanitize_untrusted_text(self.organ_name, 250) or "Órgão Público"
        clean_date = sanitize_untrusted_text(self.issue_date, 30) or "N/D"
        clean_doc_num = sanitize_untrusted_text(self.document_number, 100) or "S/N"
        clean_subquota = sanitize_untrusted_text(self.subquota_description, 200) or "Geral"
        clean_prov = sanitize_untrusted_text(self.provenance_sha256, 64)
        if len(clean_prov) != 64:
            raise ValueError("provenance_sha256 deve ser um hash hexadecimal de 64 caracteres.")
        clean_url = sanitize_untrusted_text(self.official_source_url, 500)

        object.__setattr__(self, "expense_id", clean_id)
        object.__setattr__(self, "public_agent_id", clean_agent_id)
        object.__setattr__(self, "public_agent_name", clean_agent_name)
        object.__setattr__(self, "supplier_name", clean_supplier_name)
        object.__setattr__(self, "supplier_doc", clean_supplier_doc)
        object.__setattr__(self, "organ_name", clean_organ)
        object.__setattr__(self, "issue_date", clean_date)
        object.__setattr__(self, "document_number", clean_doc_num)
        object.__setattr__(self, "subquota_description", clean_subquota)
        object.__setattr__(self, "committed_amount_brl", Decimal(str(self.committed_amount_brl)).quantize(Decimal("0.01")))
        object.__setattr__(self, "liquidated_amount_brl", Decimal(str(self.liquidated_amount_brl)).quantize(Decimal("0.01")))
        object.__setattr__(self, "paid_amount_brl", Decimal(str(self.paid_amount_brl)).quantize(Decimal("0.01")))
        object.__setattr__(self, "provenance_sha256", clean_prov)
        object.__setattr__(self, "official_source_url", clean_url)


@dataclass(frozen=True, slots=True)
class CivicEntityProfile:
    """Perfil cívico unificado de entidade pública (Fornecedor, Mandatário ou Órgão) (SPEC-0020 / FR-043)."""

    entity_type: str  # 'FORNECEDOR', 'REPRESENTANTE', 'ORGAO'
    entity_id: str
    legal_name: str
    trade_name: str
    document_masked: str
    metrics: dict[str, object]
    corporate_members: tuple[dict[str, object], ...] = field(default_factory=tuple)
    recent_contracts: tuple[dict[str, object], ...] = field(default_factory=tuple)
    recent_expenses: tuple[dict[str, object], ...] = field(default_factory=tuple)
    audit_signals: tuple[dict[str, object], ...] = field(default_factory=tuple)
    provenance_hashes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.entity_type not in ("FORNECEDOR", "REPRESENTANTE", "ORGAO"):
            raise ValueError(f"entity_type inválido: {self.entity_type}. Deve ser FORNECEDOR, REPRESENTANTE ou ORGAO.")
        clean_id = sanitize_untrusted_text(self.entity_id, 80)
        if not clean_id:
            raise ValueError("entity_id é obrigatório.")
        clean_legal = sanitize_untrusted_text(self.legal_name, 250) or clean_id
        clean_trade = sanitize_untrusted_text(self.trade_name, 250) or clean_legal
        clean_doc = sanitize_untrusted_text(self.document_masked, 50) or clean_id

        object.__setattr__(self, "entity_id", clean_id)
        object.__setattr__(self, "legal_name", clean_legal)
        object.__setattr__(self, "trade_name", clean_trade)
        object.__setattr__(self, "document_masked", clean_doc)


VALID_WATCHLIST_ENTITY_TYPES = ("FORNECEDOR", "MANDATARIO", "ORGAO", "CONTRATO", "DOSSIE")
VALID_WATCHLIST_EVENT_TYPES = (
    "NOVO_DOCUMENTO",
    "ALTERACAO_VALOR",
    "NOVO_PAGAMENTO",
    "NOVA_ANALISE",
    "RESPOSTA_CONTESTACAO",
)
VALID_WATCHLIST_FREQUENCIES = ("IMEDIATA", "DIARIA", "SEMANAL")
VALID_WATCHLIST_CHANNELS = ("NAVEGADOR_LOCAL", "WEBHOOK_CADASTRADO")


@dataclass(frozen=True, slots=True)
class CivicWatchlistSubscription:
    """Assinatura imutável de acompanhamento cívico (SPEC-0021 / FR-046)."""

    subscription_id: str
    entity_type: str
    entity_id: str
    entity_name: str
    monitored_events: tuple[str, ...]
    frequency: str = "DIARIA"
    channel: str = "NAVEGADOR_LOCAL"
    is_active: bool = True
    created_at: str = ""
    sha256: str = ""

    def __post_init__(self) -> None:
        if self.entity_type not in VALID_WATCHLIST_ENTITY_TYPES:
            raise ValueError(
                f"entity_type inválido: {self.entity_type}. Deve ser um de: {VALID_WATCHLIST_ENTITY_TYPES}"
            )
        if self.frequency not in VALID_WATCHLIST_FREQUENCIES:
            raise ValueError(
                f"frequency inválida: {self.frequency}. Deve ser uma de: {VALID_WATCHLIST_FREQUENCIES}"
            )
        if self.channel not in VALID_WATCHLIST_CHANNELS:
            raise ValueError(
                f"channel inválido: {self.channel}. Deve ser um de: {VALID_WATCHLIST_CHANNELS}"
            )
        clean_sub_id = sanitize_untrusted_text(self.subscription_id, 80)
        clean_ent_id = sanitize_untrusted_text(self.entity_id, 80)
        clean_ent_name = sanitize_untrusted_text(self.entity_name, 250) or clean_ent_id
        if not clean_sub_id or not clean_ent_id:
            raise ValueError("subscription_id e entity_id são obrigatórios.")

        clean_events = tuple(
            evt for evt in self.monitored_events if evt in VALID_WATCHLIST_EVENT_TYPES
        )
        if not clean_events:
            clean_events = ("NOVO_DOCUMENTO",)

        created = sanitize_untrusted_text(self.created_at, 40)
        if not created:
            created = datetime.now(timezone.utc).isoformat()

        hash_val = sanitize_untrusted_text(self.sha256, 64)
        if len(hash_val) != 64:
            hash_val = compute_sha256_text(
                f"{clean_sub_id}|{self.entity_type}|{clean_ent_id}|{','.join(clean_events)}|{created}"
            )

        object.__setattr__(self, "subscription_id", clean_sub_id)
        object.__setattr__(self, "entity_id", clean_ent_id)
        object.__setattr__(self, "entity_name", clean_ent_name)
        object.__setattr__(self, "monitored_events", clean_events)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "sha256", hash_val)


@dataclass(frozen=True, slots=True)
class CivicWatchlistEvent:
    """Evento público notificado para uma entidade acompanhada (SPEC-0021 / FR-046)."""

    event_id: str
    subscription_id: str
    entity_type: str
    entity_id: str
    event_type: str
    title: str
    description: str
    occurred_at: str
    payload_sha256: str
    is_read: bool = False

    def __post_init__(self) -> None:
        clean_evt_id = sanitize_untrusted_text(self.event_id, 80)
        clean_sub_id = sanitize_untrusted_text(self.subscription_id, 80)
        clean_ent_id = sanitize_untrusted_text(self.entity_id, 80)
        if not clean_evt_id or not clean_sub_id or not clean_ent_id:
            raise ValueError("event_id, subscription_id e entity_id são obrigatórios.")

        clean_type = self.event_type if self.event_type in VALID_WATCHLIST_EVENT_TYPES else "NOVO_DOCUMENTO"
        clean_title = sanitize_untrusted_text(self.title, 200) or "Novo Evento Público"
        clean_desc = sanitize_untrusted_text(self.description, 500) or "Registro de ato administrativo oficial"
        clean_date = sanitize_untrusted_text(self.occurred_at, 40) or datetime.now(timezone.utc).isoformat()
        clean_hash = sanitize_untrusted_text(self.payload_sha256, 64)
        if len(clean_hash) != 64:
            raise ValueError("payload_sha256 deve ser um hash hexadecimal de 64 caracteres.")

        object.__setattr__(self, "event_id", clean_evt_id)
        object.__setattr__(self, "subscription_id", clean_sub_id)
        object.__setattr__(self, "entity_id", clean_ent_id)
        object.__setattr__(self, "event_type", clean_type)
        object.__setattr__(self, "title", clean_title)
        object.__setattr__(self, "description", clean_desc)
        object.__setattr__(self, "occurred_at", clean_date)
        object.__setattr__(self, "payload_sha256", clean_hash)


@dataclass(frozen=True, slots=True)
class DataSourceSpecification:
    """Especificação técnica e epistemológica de fonte de dados oficial (SPEC-0021 / FR-047)."""

    source_id: str
    name: str
    governing_body: str
    official_url: str
    temporal_coverage: str
    geographic_coverage: str
    sync_frequency: str
    key_fields: tuple[str, ...]
    privacy_sanitizations: tuple[str, ...]
    epistemic_limitations: tuple[str, ...]
    version: str
    last_sync_utc: str


def get_official_data_source_catalog() -> tuple[DataSourceSpecification, ...]:
    """Retorna o catálogo completo das 8 fontes oficiais integradas com metadados e limitações."""
    return (
        DataSourceSpecification(
            source_id="CAMARA_CEAP",
            name="Cota para o Exercício da Atividade Parlamentar (CEAP)",
            governing_body="Câmara dos Deputados",
            official_url="https://dadosabertos.camara.leg.br",
            temporal_coverage="2019-2026",
            geographic_coverage="Federal (Câmara dos Deputados)",
            sync_frequency="Diária",
            key_fields=("numAno", "numMes", "txtFornecedor", "txtCNPJCPF", "vlrLiquido", "urlDocumento"),
            privacy_sanitizations=("Mascaramento estrito de CPF (***.XXX.XXX-**)", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Reembolsos dependem de homologação administrativa interna.",
                "Emissão de nota fiscal em final de semana ou feriado pode refletir prestação contínua de serviço.",
            ),
            version="1.3.0",
            last_sync_utc="2026-10-26T12:00:00Z",
        ),
        DataSourceSpecification(
            source_id="SENADO_CEAPS",
            name="Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS)",
            governing_body="Senado Federal",
            official_url="https://legis.senado.leg.br/dadosabertos",
            temporal_coverage="2019-2026",
            geographic_coverage="Federal (Senado Federal)",
            sync_frequency="Diária",
            key_fields=("ANO", "MES", "SENADOR", "FORNECEDOR", "CNPJ_CPF", "VALOR_REEMBOLSADO"),
            privacy_sanitizations=("Mascaramento estrito de CPF (***.XXX.XXX-**)", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Regras regimentais do Senado possuem tetos cumulativos diferenciados.",
                "Valores passíveis de estorno contábil posterior.",
            ),
            version="1.2.0",
            last_sync_utc="2026-10-26T12:00:00Z",
        ),
        DataSourceSpecification(
            source_id="CGU_EMENDAS",
            name="Emendas Parlamentares e Transferências Especiais",
            governing_body="Controladoria-Geral da União (CGU) / Portal da Transparência",
            official_url="https://portaldatransparencia.gov.br",
            temporal_coverage="2020-2026",
            geographic_coverage="Nacional (Transferências da União a Estados e Municípios)",
            sync_frequency="Diária",
            key_fields=("codigoEmenda", "autorEmenda", "tipoEmenda", "valorEmpenhado", "valorLiquidado", "valorPago"),
            privacy_sanitizations=("Preservação do mascaramento CGU de CPF", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Diferença entre empenhado e pago reflete o ciclo orçamentário regular.",
                "Execução descentralizada sob responsabilidade do ente recebedor.",
            ),
            version="1.4.0",
            last_sync_utc="2026-10-26T06:00:00Z",
        ),
        DataSourceSpecification(
            source_id="PNCP_CONTRATOS",
            name="Portal Nacional de Contratações Públicas (PNCP) - Contratos e Editais",
            governing_body="Ministério da Gestão e da Inovação em Serviços Públicos (MGI)",
            official_url="https://pncp.gov.br",
            temporal_coverage="2021-2026",
            geographic_coverage="Nacional (União, Estados e Municípios)",
            sync_frequency="Diária",
            key_fields=("numeroControlePNCP", "orgaoEntidade", "valorGlobal", "objetoContrato", "cnpjContratado"),
            privacy_sanitizations=("Mascaramento de CPF de representantes legais", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Adesão gradual de municípios de pequeno porte conforme cronograma da Lei 14.133/21.",
                "Aditivos contratuais constituem instrumentos regulares admitidos em lei.",
            ),
            version="1.5.0",
            last_sync_utc="2026-10-26T06:00:00Z",
        ),
        DataSourceSpecification(
            source_id="CGU_CEIS",
            name="Cadastro Nacional de Empresas Inidôneas e Suspensas (CEIS)",
            governing_body="Controladoria-Geral da União (CGU)",
            official_url="https://portaldatransparencia.gov.br/sancoes/ceis",
            temporal_coverage="2015-2026",
            geographic_coverage="Nacional (Todas as esferas administrativas)",
            sync_frequency="Diária",
            key_fields=("codigoSancao", "cpfCnpjSancionado", "nomeSancionado", "dataInicioSancao", "dataFimSancao"),
            privacy_sanitizations=("Mascaramento LGPD de CPF sancionado", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Sanções expiradas perdem vigência automaticamente.",
                "Extensão de sanção a pessoas jurídicas coligadas requer desconsideração formal da personalidade.",
            ),
            version="1.2.0",
            last_sync_utc="2026-10-26T08:00:00Z",
        ),
        DataSourceSpecification(
            source_id="CGU_CNEP",
            name="Cadastro Nacional de Empresas Punidas (CNEP - Lei Anticorrupção)",
            governing_body="Controladoria-Geral da União (CGU)",
            official_url="https://portaldatransparencia.gov.br/sancoes/cnep",
            temporal_coverage="2014-2026",
            geographic_coverage="Nacional",
            sync_frequency="Diária",
            key_fields=("codigoSancao", "cnpjSancionado", "razaoSocial", "valorMulta", "dataPublicacao"),
            privacy_sanitizations=("Hash SHA-256 do lote bruto", "Validação de CNPJ de 14 dígitos"),
            epistemic_limitations=(
                "Acordos de leniência podem suspender efeitos sancionatórios.",
                "Efeitos de sanções restritos aos termos exatos da decisão administrativa.",
            ),
            version="1.2.0",
            last_sync_utc="2026-10-26T08:00:00Z",
        ),
        DataSourceSpecification(
            source_id="TSE_ELEICOES",
            name="Repositório de Dados Eleitorais - Prestação de Contas de Campanha",
            governing_body="Tribunal Superior Eleitoral (TSE)",
            official_url="https://dadosabertos.tse.jus.br",
            temporal_coverage="2018-2024",
            geographic_coverage="Nacional (Eleições Gerais e Municipais)",
            sync_frequency="Semanal / Periódica",
            key_fields=("anoEleicao", "sqCandidato", "nomeCandidato", "cpfCnpjDoador", "nomeDoador", "valorDoacao"),
            privacy_sanitizations=("Mascaramento estrito de CPF de doador PF", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Doações de campanha declaradas à Justiça Eleitoral constituem atos legais e legítimos.",
                "Não há presunção automática de favorecimento indevido em contratações posteriores.",
            ),
            version="1.1.0",
            last_sync_utc="2026-10-24T18:00:00Z",
        ),
        DataSourceSpecification(
            source_id="RECEITA_FEDERAL_CNPJ",
            name="Cadastro Nacional da Pessoa Jurídica (Dados Abertos CNPJ e QSA)",
            governing_body="Receita Federal do Brasil (RFB)",
            official_url="https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica-cnpj",
            temporal_coverage="1960-2026",
            geographic_coverage="Nacional",
            sync_frequency="Mensal",
            key_fields=("cnpj", "razaoSocial", "dataAbertura", "capitalSocial", "cnaePrincipal", "sociosQSA"),
            privacy_sanitizations=("Mascaramento de CPF de sócios e administradores", "Hash SHA-256 do lote bruto"),
            epistemic_limitations=(
                "Defasagem natural entre alteração na Junta Comercial e publicação em dados abertos.",
                "Participação de sócio como mero cotista sem gerência é legalmente admitida.",
            ),
            version="1.3.0",
            last_sync_utc="2026-10-15T00:00:00Z",
        ),
    )




"""Unit and integration tests for SPEC-0016 (Conflito de Interesses: Agente Público no QSA de Fornecedor)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import evaluate_public_agent_supplier_crossmatch_rule
from deolhonobrasil.pipeline.models import (
    CuratedCorporateMemberRecord,
    CuratedPublicAgentRecord,
    CuratedPublicContract,
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


class TestPublicAgentSupplierCrossmatchRules(unittest.TestCase):
    """Verifies SPEC-0016 public agent domain model, anti-homonym logic, and deterministic crossmatch rule."""

    def setUp(self) -> None:
        self.servidor_provenance = ProvenanceMetadata(
            source=OfficialSource.PORTAL_TRANSPARENCIA_SERVIDORES,
            source_url="https://portaldatransparencia.gov.br/servidores",
            source_record_id="SERV-BATCH-001",
            collected_at_utc="2026-10-25T14:00:00Z",
            raw_batch_sha256="1" * 64,
        )
        self.rfb_provenance = ProvenanceMetadata(
            source=OfficialSource.RECEITA_FEDERAL_CNPJ,
            source_url="https://dadosabertos.rfb.gov.br/CNPJ/socios.zip",
            source_record_id="RFB-QSA-BATCH-001",
            collected_at_utc="2026-10-25T14:05:00Z",
            raw_batch_sha256="2" * 64,
        )
        self.pncp_provenance = ProvenanceMetadata(
            source=OfficialSource.PNCP_CONTRATOS,
            source_url="https://pncp.gov.br/api/consulta/v1/contratos",
            source_record_id="PNCP-BATCH-001",
            collected_at_utc="2026-10-25T14:10:00Z",
            raw_batch_sha256="3" * 64,
        )
        self.ceap_provenance = ProvenanceMetadata(
            source=OfficialSource.CAMARA_CEAP,
            source_url="https://dadosabertos.camara.leg.br/api/v2/deputados/despesas",
            source_record_id="CEAP-BATCH-001",
            collected_at_utc="2026-10-25T14:15:00Z",
            raw_batch_sha256="4" * 64,
        )

    def test_public_agent_model_validation_and_masking(self) -> None:
        """`FR-034`, `DATA-018`, `SEC-019`, `AC-062`: Validates CuratedPublicAgentRecord creation, CPF masking, and immutability."""
        agent = CuratedPublicAgentRecord.create_validated(
            agent_id="SIAPE-987654",
            organ_code="12.345.678/0001-95",
            organ_name="Ministério da Gestão e Inovação",
            agent_name="Mariana Souza Alcantara",
            agent_doc_raw="***.847.291-**",
            position_title="Analista de Planejamento e Orçamento",
            status="ATIVO",
            provenance=self.servidor_provenance,
        )

        self.assertEqual(agent.agent_id, "SIAPE-987654")
        self.assertEqual(agent.organ_code, "12.345.678/0001-95")
        self.assertEqual(agent.organ_name, "Ministério da Gestão e Inovação")
        self.assertEqual(agent.agent_name, "Mariana Souza Alcantara")
        self.assertEqual(agent.agent_doc_masked, "***.847.291-**")
        self.assertEqual(agent.position_title, "Analista de Planejamento e Orçamento")
        self.assertEqual(agent.status, "ATIVO")
        self.assertTrue(len(agent.natural_key) == 64)

        # Imutabilidade (frozen dataclass)
        with self.assertRaises(AttributeError):
            agent.agent_name = "Outro Nome"  # type: ignore[misc]

        # Validação de CPF inválido ou vazio
        with self.assertRaises(ValueError):
            CuratedPublicAgentRecord.create_validated(
                agent_id="SIAPE-001",
                organ_code="12.345.678/0001-95",
                organ_name="Órgão Exemplo",
                agent_name="Nome Válido",
                agent_doc_raw="invalido",
                position_title="Cargo",
                provenance=self.servidor_provenance,
            )

    def test_public_agent_supplier_rule_detects_conflict_in_same_organ(self) -> None:
        """`FR-035`, `NFR-019`, `AC-063`: Detects public agent in QSA of supplier contracted by their own organ."""
        agent = CuratedPublicAgentRecord.create_validated(
            agent_id="SIAPE-112233",
            organ_code="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            agent_name="Roberto Mendes Ribeiro",
            agent_doc_raw="***.334.556-**",
            position_title="Coordenador Geral de Logística",
            status="ATIVO",
            provenance=self.servidor_provenance,
        )

        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Roberto Mendes Ribeiro",
            member_doc_masked="***.334.556-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2021-06-01",
            provenance=self.rfb_provenance,
        )

        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-CONTRATO-2024-001",
            organ_cnpj_raw="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Mendes & Ribeiro Soluções em Saúde Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Fornecimento continuado de insumos médico-hospitalares",
            signature_date=date(2024, 3, 1),
            initial_amount_raw=Decimal("450000.00"),
            current_amount_raw=Decimal("450000.00"),
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        expense = CuratedPublicExpense.create_validated(
            competence_year=2024,
            competence_month=4,
            issue_date=date(2024, 4, 15),
            sphere="FEDERAL",
            organ_code="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            public_agent_id="DEP-001",
            public_agent_name="Parlamentar A",
            party_sigla="PART",
            state_uf="DF",
            expense_category="Locação de Bens",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Mendes & Ribeiro Soluções em Saúde Ltda",
            document_number="NF-99881",
            gross_amount_raw=Decimal("15000.00"),
            net_amount_raw=Decimal("15000.00"),
            document_evidence_url="https://portal.exemplo.gov.br/doc/99881.pdf",
            provenance=self.ceap_provenance,
        )

        # Testar com contratos
        signals_contract = evaluate_public_agent_supplier_crossmatch_rule(
            agents=[agent],
            corporate_members=[member],
            contracts=[contract],
        )
        self.assertEqual(len(signals_contract), 1)
        sig = signals_contract[0]
        self.assertEqual(sig.rule_code, "R-CROSS-PUBLIC-AGENT-SUPPLIER")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(sig.metric_value, Decimal("450000.00"))
        self.assertEqual(len(sig.provenance_hashes), 3)

        # Testar com despesas
        signals_expense = evaluate_public_agent_supplier_crossmatch_rule(
            agents=[agent],
            corporate_members=[member],
            expenses=[expense],
        )
        self.assertEqual(len(signals_expense), 1)
        sig_exp = signals_expense[0]
        self.assertEqual(sig_exp.rule_code, "R-CROSS-PUBLIC-AGENT-SUPPLIER")
        self.assertEqual(sig_exp.metric_value, Decimal("15000.00"))
        self.assertEqual(len(sig_exp.provenance_hashes), 3)

    def test_public_agent_supplier_rule_ignores_different_organ(self) -> None:
        """`FR-035`, `NFR-019`, `AC-064`: Discards signal when public agent belongs to a different contracting organ."""
        # Agente lotado no Órgão B (ex: Petrobras)
        agent = CuratedPublicAgentRecord.create_validated(
            agent_id="PETRO-554433",
            organ_code="33.000.167/0001-01",
            organ_name="Petróleo Brasileiro S.A.",
            agent_name="Fernanda Lima Castro",
            agent_doc_raw="***.112.998-**",
            position_title="Engenheira de Equipamentos",
            status="ATIVO",
            provenance=self.servidor_provenance,
        )

        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Fernanda Lima Castro",
            member_doc_masked="***.112.998-**",
            qualification_code="22",
            qualification_description="Sócio",
            entry_date="2022-01-10",
            provenance=self.rfb_provenance,
        )

        # Contrato com Órgão A (ex: Ministério da Saúde - 12.345.678/0001-95)
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-CONTRATO-2024-002",
            organ_cnpj_raw="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Castro Soluções em Engenharia Ltda",
            modality_name="Concorrência",
            contract_object="Consultoria técnica especializada",
            signature_date=date(2024, 2, 10),
            initial_amount_raw=Decimal("120000.00"),
            current_amount_raw=Decimal("120000.00"),
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        signals = evaluate_public_agent_supplier_crossmatch_rule(
            agents=[agent],
            corporate_members=[member],
            contracts=[contract],
        )
        # Como o agente é da Petrobras e o contrato é do Ministério da Saúde, não há conflito direto de órgão
        self.assertEqual(len(signals), 0)

    def test_public_agent_supplier_rule_ignores_unrelated_members(self) -> None:
        """`FR-035`, `AC-065`: Discards signal when corporate members do not match public agents in name or document."""
        agent = CuratedPublicAgentRecord.create_validated(
            agent_id="SIAPE-778899",
            organ_code="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            agent_name="Juliana Barbosa Prado",
            agent_doc_raw="***.445.667-**",
            position_title="Auditora Fiscal",
            status="ATIVO",
            provenance=self.servidor_provenance,
        )

        unrelated_member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Pedro Alcantara Guimaraes",
            member_doc_masked="***.998.776-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-05-12",
            provenance=self.rfb_provenance,
        )

        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-CONTRATO-2024-003",
            organ_cnpj_raw="12.345.678/0001-95",
            organ_name="Ministério da Saúde",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Alcantara Guimaraes Comércio Ltda",
            modality_name="Dispensa de Licitação",
            contract_object="Fornecimento de equipamentos de informática",
            signature_date=date(2024, 5, 20),
            initial_amount_raw=Decimal("45000.00"),
            current_amount_raw=Decimal("45000.00"),
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        signals = evaluate_public_agent_supplier_crossmatch_rule(
            agents=[agent],
            corporate_members=[unrelated_member],
            contracts=[contract],
        )
        self.assertEqual(len(signals), 0)


if __name__ == "__main__":
    unittest.main()

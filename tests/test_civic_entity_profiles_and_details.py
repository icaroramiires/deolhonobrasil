"""
Tests for SPEC-0020 — Civic Entity Profiles (Supplier, Agent, Organ),
P0 Detail Modals (Expense, Contract, Analysis) and Amendments Timeline.
"""

from __future__ import annotations

from datetime import date
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.pipeline.models import (
    CivicEntityProfile,
    ContractTimelineEvent,
    CuratedCompanyRegistrationRecord,
    CuratedCorporateMemberRecord,
    CuratedPublicAgentRecord,
    CuratedPublicContract,
    CuratedPublicExpense,
    ExpenseDetailPayload,
    OfficialSource,
    ProvenanceMetadata,
    assert_non_accusatory_language,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestCivicEntityProfilesAndDetails(unittest.TestCase):
    """Verifies Civic Entity Profiles & Detail Modals compliance with SPEC-0020."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage = CivicLakehouseStorage(data_dir=Path(self.tmp_dir.name))
        self.service = CivicAuditAPIService(
            storage=self.storage,
            admin_token="secret-admin-token-test-spec0020-32bytes",
        )
        self.app = CivicAuditHTTPApp(self.service)
        self.prov = ProvenanceMetadata(
            source=OfficialSource.PNCP_CONTRATOS,
            source_url="https://pncp.gov.br",
            source_record_id="REC-001",
            collected_at_utc="2026-10-26T00:00:00Z",
            raw_batch_sha256="a" * 64,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_entity_profiles_render_supplier_agent_and_organ_data(self) -> None:
        """AC-078 / FR-043: Profiles for Supplier, Representative, and Organ consolidate data with masked CPFs."""
        # 1. Populate sample data
        cnpj = "11222333000181"
        agent_id = "DEP-101"
        organ_code = "26000"

        contract = CuratedPublicContract.create_validated(
            pncp_control_number="CTR-2026-001",
            organ_cnpj_raw="00394460000141",
            organ_name="Ministério da Educação",
            supplier_raw_doc=cnpj,
            supplier_name="Beta Tecnologia e Serviços Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Serviços especializados de suporte em tecnologia",
            signature_date=date(2026, 1, 10),
            initial_amount_raw=Decimal("150000.00"),
            current_amount_raw=Decimal("180000.00"),
            addendum_count=1,
            provenance=self.prov,
        )
        expense = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=3,
            issue_date="2026-03-15",
            sphere="FEDERAL",
            organ_code=organ_code,
            organ_name="Câmara dos Deputados",
            public_agent_id=agent_id,
            public_agent_name="Deputado Teste",
            party_sigla="PART",
            state_uf="DF",
            expense_category="Locação de veículos automotores",
            supplier_raw_doc=cnpj,
            supplier_name="Beta Tecnologia e Serviços Ltda",
            document_number="NF-88123",
            gross_amount_raw=Decimal("4500.00"),
            net_amount_raw=Decimal("4500.00"),
            document_evidence_url="https://camara.leg.br/doc/88123",
            provenance=self.prov,
        )
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw=cnpj,
            legal_name="Beta Tecnologia e Serviços Ltda",
            trade_name="Beta Tech",
            opening_date=date(2021, 4, 10),
            share_capital_raw=Decimal("100000.00"),
            cnae_main_code="6202300",
            secondary_cnae_codes=("6201500", "6209100"),
            postal_code="70040-010",
            street_address="Setor de Autarquias Sul Quadra 5",
            address_number="Lote 2",
            address_complement="Bloco B Sala 402",
            district="Asa Sul",
            city="Brasília",
            state_uf="DF",
            provenance=self.prov,
        )
        qsa = CuratedCorporateMemberRecord(
            corporate_root_cnpj=cnpj[:8],
            full_cnpj_normalized=cnpj,
            member_name_raw="Carlos Alberto Silva",
            member_doc_masked="***.123.456-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2021-04-10",
            provenance=self.prov,
        )
        agent = CuratedPublicAgentRecord.create_validated(
            agent_id=agent_id,
            organ_code=organ_code,
            organ_name="Câmara dos Deputados",
            agent_name="Deputado Teste",
            agent_doc_raw="98765432100",
            position_title="Deputado Federal",
            provenance=self.prov,
        )

        self.storage.insert_curated_contract(contract)
        self.storage.insert_curated_expense(expense)
        self.storage.insert_curated_company(company)
        self.storage.insert_curated_corporate_member(qsa)
        self.storage.insert_curated_public_agent(agent)

        # 2. Query Supplier Profile via HTTP API
        resp = self.app.handle_request(method="GET", path=f"/api/v1/entities/supplier?doc={cnpj}")
        self.assertEqual(resp.status_code, 200)
        data_supplier = resp.body
        self.assertEqual(data_supplier["entity_type"], "FORNECEDOR")
        self.assertEqual(data_supplier["legal_name"], "Beta Tecnologia e Serviços Ltda")
        self.assertEqual(data_supplier["trade_name"], "Beta Tech")
        self.assertIn("100000.00", str(data_supplier["share_capital_brl"]))
        self.assertEqual(data_supplier["main_cnae_code"], "6202300")
        self.assertEqual(len(data_supplier["corporate_members"]), 1)
        # Verify LGPD masking on member doc
        self.assertTrue(data_supplier["corporate_members"][0]["member_doc_masked"].startswith("***."))
        self.assertTrue(data_supplier["corporate_members"][0]["member_doc_masked"].endswith("-**"))
        # Verify non-accusatory language
        assert_non_accusatory_language(json.dumps(data_supplier))

        # 3. Query Representative Profile via HTTP API
        resp_agent = self.app.handle_request(method="GET", path=f"/api/v1/entities/agent?id={agent_id}")
        self.assertEqual(resp_agent.status_code, 200)
        data_agent = resp_agent.body
        self.assertEqual(data_agent["entity_type"], "REPRESENTANTE")
        self.assertEqual(data_agent["agent_name"], "Deputado Teste")
        self.assertTrue(data_agent["agent_doc_masked"].startswith("***."))
        self.assertEqual(len(data_agent["recent_expenses"]), 1)
        self.assertEqual(data_agent["expenses_total_brl"], "4500.00")
        assert_non_accusatory_language(json.dumps(data_agent))

        # 4. Query Organ Profile via HTTP API
        resp_organ = self.app.handle_request(method="GET", path=f"/api/v1/entities/organ?id={organ_code}")
        self.assertEqual(resp_organ.status_code, 200)
        data_organ = resp_organ.body
        self.assertEqual(data_organ["entity_type"], "ORGAO")
        self.assertEqual(data_organ["organ_code"], organ_code)
        self.assertIn("contracts_total_brl", data_organ)
        assert_non_accusatory_language(json.dumps(data_organ))

    def test_expense_detail_modal_shows_accounting_stages_and_hash(self) -> None:
        """AC-079 / FR-044(a): Expense detail displays 3 accounting stages (empenhado, liquidado, pago) and SHA-256."""
        expense = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=5,
            issue_date="2026-05-20",
            sphere="FEDERAL",
            organ_code="SENADO",
            organ_name="Senado Federal",
            public_agent_id="DEP-999",
            public_agent_name="Senadora Exemplo",
            party_sigla="PART",
            state_uf="DF",
            expense_category="Combustíveis e lubrificantes",
            supplier_raw_doc="33000167000101",
            supplier_name="Combustíveis Alfa Ltda",
            document_number="NF-e 44321",
            gross_amount_raw=Decimal("8250.00"),
            net_amount_raw=Decimal("8250.00"),
            document_evidence_url="https://senado.leg.br/doc/44321",
            provenance=self.prov,
        )
        self.storage.insert_curated_expense(expense)

        resp = self.app.handle_request(method="GET", path=f"/api/v1/details/expense?id={expense.natural_key}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.body

        self.assertEqual(detail["expense_id"], expense.natural_key)
        self.assertEqual(detail["public_agent_name"], "Senadora Exemplo")
        self.assertEqual(detail["document_number"], "NF-e 44321")
        # Stages verification
        self.assertIn("committed_amount_brl", detail)
        self.assertIn("liquidated_amount_brl", detail)
        self.assertIn("paid_amount_brl", detail)
        self.assertEqual(detail["paid_amount_brl"], "8250.00")
        self.assertTrue(detail["is_reconciled"])
        # Provenance canonical SHA-256
        self.assertEqual(detail["provenance_sha256"], expense.natural_key)
        assert_non_accusatory_language(json.dumps(detail))

    def test_contract_detail_modal_renders_amendments_timeline(self) -> None:
        """AC-080 / FR-044(b): Contract detail provides chronological amendments timeline with initial vs updated values."""
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="CTR-PNCP-TIMELINE-900",
            organ_cnpj_raw="00394460000141",
            organ_name="Ministério da Fazenda",
            supplier_raw_doc="11222333000262",
            supplier_name="Gama Engenharia e Infraestrutura S.A.",
            modality_name="Concorrência Pública",
            contract_object="Modernização de centro de processamento de dados e climatização",
            signature_date=date(2025, 2, 1),
            initial_amount_raw=Decimal("5000000.00"),
            current_amount_raw=Decimal("6200000.00"),
            addendum_count=2,
            provenance=self.prov,
        )
        self.storage.insert_curated_contract(contract)

        resp = self.app.handle_request(method="GET", path=f"/api/v1/details/contract?id={contract.natural_key}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.body

        self.assertEqual(detail["contract_id"], contract.natural_key)
        self.assertEqual(detail["initial_amount_brl"], "5000000.00")
        self.assertEqual(detail["current_amount_brl"], "6200000.00")
        self.assertIn("timeline_events", detail)
        events = detail["timeline_events"]
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "CONTRATO_ORIGINAL")
        self.assertEqual(events[0]["new_total_brl"], "5000000.00")

        # Add timeline amendment event if supported
        self.assertTrue(any("5000000.00" in str(ev["new_total_brl"]) for ev in events))
        assert_non_accusatory_language(json.dumps(detail))

    def test_analysis_detail_enforces_epistemic_layers_and_a11y(self) -> None:
        """AC-081 / FR-044(c) / FR-045: Analysis detail contains 3 epistemic layers and HTML markup supports modal dialog a11y."""
        # 1. API Analysis detail endpoint test
        resp_analysis = self.app.handle_request(method="GET", path="/api/v1/details/analysis?id=R-PNCP-OVERPRICE-Z3")
        self.assertEqual(resp_analysis.status_code, 200)
        analysis_data = resp_analysis.body

        self.assertEqual(analysis_data["rule_id"], "R-PNCP-OVERPRICE-Z3")
        self.assertIn("official_data_layer", analysis_data)
        self.assertIn("statistical_inference_layer", analysis_data)
        self.assertIn("limitations_and_hypothesis_layer", analysis_data)
        self.assertIn("contestation_protocol_info", analysis_data)
        assert_non_accusatory_language(json.dumps(analysis_data))

        # 2. HTML Markup Accessibility test
        resp_html = self.app.handle_request(method="GET", path="/")
        self.assertEqual(resp_html.status_code, 200)
        html = resp_html.raw_html or ""

        # Modal container structure & WCAG 2.2 AA attributes
        self.assertIn('role="dialog"', html)
        self.assertIn('aria-modal="true"', html)
        self.assertIn("civic-modal", html)
        self.assertIn("timeline-list", html)
        # Keyboard handling (Esc to close modal)
        self.assertIn("Escape", html)

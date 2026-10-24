"""CLI oficial do pipeline de dados De Olho no Brasil (Ingestão, Validação e Reconciliação)."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from deolhonobrasil.audit.laya_engine import LayaSystem1Adapter
from deolhonobrasil.audit.rag_narrator import GroundedDossierNarrator
from deolhonobrasil.audit.rules import evaluate_ceap_quota_outlier_rule
from deolhonobrasil.governance.dossiers import (
    AccessRole,
    AuditDossier,
    DossierStatus,
    approve_dossier_for_publication,
    attach_right_of_reply,
)
from deolhonobrasil.governance.right_of_reply import (
    RightOfReplyStatus,
    RightOfReplySubmission,
)
from deolhonobrasil.pipeline.connectors.camara_ceap import parse_camara_ceap_csv_batch
from deolhonobrasil.pipeline.connectors.cgu_transparencia import parse_cgu_amendments_json_batch
from deolhonobrasil.pipeline.connectors.pncp_contratos import parse_pncp_contracts_json_batch
from deolhonobrasil.pipeline.connectors.senado_ceaps import parse_senado_ceaps_csv_batch
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage

SAMPLE_CAMARA_CSV = """ideDocumento;numAno;numMes;datEmissao;ideCadastro;txNomeParlamentar;sgPartido;sgUF;txtDescricao;txtCNPJCPF;txtFornecedor;txtNumero;vlrDocumento;vlrLiquido;urlDocumento
7841920;2026;9;2026-09-14;204554;Parlamentar Exemplo A;PART-A;SP;DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.;00.000.000/0001-91;BANCO DO BRASIL SA (EXEMPLO TESTE);NF-001;12500,50;12500,50;https://www.camara.leg.br/cota-parlamentar/documentos/publ/7841920.pdf
7841921;2026;9;2026-09-15;204555;Parlamentar Exemplo B;PART-B;MG;LOCAÇÃO OU FRETAMENTO DE VEÍCULOS AUTOMOTORES;52998224725;LOCADOR PF EXEMPLO (CPF SERA MASCARADO LGPD);REC-099;4200,00;4200,00;https://www.camara.leg.br/cota-parlamentar/documentos/publ/7841921.pdf
;2026;9;2026-09-16;204556;Registro Invalido Sem ID;PART-C;RJ;COMBUSTÍVEIS E LUBRIFICANTES.;00.000.000/0001-91;POSTO EXEMPLO;NF-ERR;150,00;150,00;
"""

SAMPLE_SENADO_CSV = """COD_DOCUMENTO;ANO;MES;DATA;COD_SENADOR;SENADOR;PARTIDO;UF;TIPO_DESPESA;CNPJ_CPF;FORNECEDOR;DOCUMENTO;VALOR_REEMBOLSADO
99201;2026;8;28/08/2026;5012;Senador Exemplo C;PART-S;RS;Passagens aéreas, aquáticas e terrestres nacionais;00.000.000/0001-91;COMPANHIA AEREA EXEMPLO;BIL-778;3410,20
99202;2026;8;29/08/2026;5013;Senador Com Valor Ausente;PART-S;BA;Aluguel de imóveis para escritório político;00.000.000/0001-91;IMOBILIARIA EXEMPLO;DOC-NULL;
"""

SAMPLE_CGU_AMENDMENTS_JSON = json.dumps(
    [
        {
            "codigoEmenda": "202681000101",
            "ano": 2026,
            "codigoAutor": "8100",
            "nomeAutor": "Bancada Exemplo Federal",
            "tipoEmenda": "Emenda de Bancada",
            "funcao": "Saúde",
            "codigoIBGEMunicipio": "3550308",
            "uf": "SP",
            "cnpjFavorecido": "00.000.000/0001-91",
            "nomeFavorecido": "Fundo Municipal de Saúde Exemplo",
            "valorEmpenhado": "500000,00",
            "valorPago": "250000,00",
        },
        {
            "codigoEmenda": "S/I",
            "ano": 2026,
            "codigoAutor": "0000",
            "nomeAutor": "Emenda Invalida Sem Codigo",
            "tipoEmenda": "Individual",
            "funcao": "Educação",
            "codigoIBGEMunicipio": "INVALIDO",
            "uf": "SP",
            "cnpjFavorecido": "00.000.000/0001-91",
            "nomeFavorecido": "Entidade",
            "valorEmpenhado": "100,00",
            "valorPago": "100,00",
        },
    ],
    ensure_ascii=False,
)

SAMPLE_PNCP_CONTRACTS_JSON = json.dumps(
    {
        "data": [
            {
                "numeroControlePNCP": "00000000000191-0-000001/2026",
                "orgaoEntidade": {
                    "cnpj": "00.000.000/0001-91",
                    "razaoSocial": "Ministério Exemplo da União",
                },
                "niFornecedor": "00.000.000/0001-91",
                "nomeRazaoSocialFornecedor": "Tecnologia Cívica S/A",
                "categoriaProcesso": "Pregão Eletrônico",
                "objetoContrato": "Contratação de serviços técnicos de infraestrutura em nuvem auditável.",
                "dataAssinatura": "2026-09-02",
                "valorInicial": "1500000.00",
                "valorGlobal": "1820000.00",
                "numeroRetificacao": 2,
            }
        ]
    },
    ensure_ascii=False,
)


def run_sample_pipeline(
    data_dir: Path,
    verify_reconciliation: bool = True,
    run_audit: bool = False,
) -> int:
    """Executa um fluxo fim a fim de validação (Raw -> Standardized -> Curated + Quarantine) e opcionalmente auditoria cívica."""
    storage = CivicLakehouseStorage(data_dir=data_dir)

    camara_bytes = SAMPLE_CAMARA_CSV.encode("utf-8")
    camara_batch = parse_camara_ceap_csv_batch(
        camara_bytes,
        source_url="https://www.camara.leg.br/cotas/Ano-2026.csv.zip",
        reported_control_total=Decimal("16700.50"),
    )
    rep_camara = storage.persist_expense_batch(camara_bytes, camara_batch)

    senado_bytes = SAMPLE_SENADO_CSV.encode("utf-8")
    senado_batch = parse_senado_ceaps_csv_batch(
        senado_bytes,
        source_url="https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2026/csv",
        reported_control_total=Decimal("3410.20"),
    )
    rep_senado = storage.persist_expense_batch(senado_bytes, senado_batch)

    cgu_bytes = SAMPLE_CGU_AMENDMENTS_JSON.encode("utf-8")
    cgu_batch = parse_cgu_amendments_json_batch(
        cgu_bytes,
        source_url="https://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano=2026",
        reported_control_total=Decimal("250000.00"),
    )
    rep_cgu = storage.persist_amendment_batch(cgu_bytes, cgu_batch)

    pncp_bytes = SAMPLE_PNCP_CONTRACTS_JSON.encode("utf-8")
    pncp_batch = parse_pncp_contracts_json_batch(
        pncp_bytes,
        source_url="https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20260901&dataFinal=20260930",
        reported_control_total=Decimal("1820000.00"),
    )
    rep_pncp = storage.persist_contract_batch(pncp_bytes, pncp_batch)

    reports = [rep_camara, rep_senado, rep_cgu, rep_pncp]
    summary = storage.get_summary_metrics()

    output: dict[str, object] = {
        "status": "SUCCESS",
        "reconciliation_reports": [
            {
                "source": r.source.value,
                "raw_batch_sha256": r.raw_batch_sha256,
                "valid_records_count": r.valid_records_count,
                "inserted_new_count": r.inserted_new_count,
                "deduplicated_skipped_count": r.deduplicated_skipped_count,
                "quarantined_count": r.quarantined_count,
                "computed_net_total": str(r.computed_net_total),
                "reported_control_total": str(r.reported_control_total),
                "is_reconciled": r.is_reconciled,
            }
            for r in reports
        ],
        "lakehouse_summary": summary,
    }

    if run_audit:
        # 1. Executar regra determinística de auditoria (R-CEAP-OUTLIER-Z3)
        sample_expense = camara_batch.valid_records[0]
        peer_expenses = [
            Decimal("1200.00"),
            Decimal("1500.00"),
            Decimal("1300.00"),
            Decimal("1400.00"),
            Decimal("1250.00"),
        ]
        signal = evaluate_ceap_quota_outlier_rule(
            expense=sample_expense,
            peer_expenses=peer_expenses,
            z_threshold=Decimal("3.00"),
        )
        if signal is None:
            raise RuntimeError("Falha na geração de sinal determinístico de auditoria.")

        # 2. Avaliação de triagem rápida pelo Laya System 1
        laya_adapter = LayaSystem1Adapter()
        laya_decision = laya_adapter.evaluate(signal)

        # 3. Grounded RAG: geração de narrativa em 3 camadas epistêmicas
        narrator = GroundedDossierNarrator()
        grounded_sections = narrator.generate(signal, laya_decision)

        # 4. Criação e persistência do dossiê em EM_TRIAGEM_INTERNA
        dossier_id = f"DOS-{signal.signal_id[:24]}"
        triage_dossier = AuditDossier(
            dossier_id=dossier_id,
            signal=signal,
            laya_decision=laya_decision,
            grounded_sections=grounded_sections,
            status=DossierStatus.EM_TRIAGEM_INTERNA,
            reviewer_id=None,
            right_of_reply=None,
            correction_note=None,
            updated_at_utc="2026-10-23T18:00:00Z",
        )
        storage.upsert_dossier(triage_dossier, actor_id="system_pipeline")

        # 5. Validação da regra estrita de visibilidade (Seção 12.4):
        # Leitor público vê 0 dossiês em triagem; revisor administrativo vê 1
        public_before = storage.list_dossiers_for_role(AccessRole.PUBLIC_READER)
        admin_before = storage.list_dossiers_for_role(AccessRole.REVIEWER_ADMIN)
        if len(public_before) != 0:
            raise RuntimeError(
                f"Violação de governança editorial: leitor público teve acesso a {len(public_before)} dossiê(s) em triagem interna!"
            )
        if len(admin_before) < 1:
            raise RuntimeError(
                "Violação de governança: revisor administrativo não encontrou o dossiê em triagem interna."
            )

        # 6. Aprovação humana por revisor identificado
        approved_dossier = approve_dossier_for_publication(
            triage_dossier,
            reviewer_id="auditor_chefe_01",
            timestamp_utc="2026-10-23T18:30:00Z",
        )

        # 7. Protocolo e vinculação de Direito de Resposta formal com paridade visual
        reply = RightOfReplySubmission(
            protocol_id=f"REP-{dossier_id}",
            dossier_id=dossier_id,
            respondent_name="Gabinete Parlamentar",
            respondent_document_masked_or_cnpj=sample_expense.supplier_doc_normalized,
            institutional_email_domain="camara.leg.br",
            statement_text="A despesa refere-se à prestação de serviços técnicos especializados de comunicação institucional, com comprovação fiscal anexa e aprovação contábil regular.",
            attachment_sha256="b" * 64,
            submitted_at_utc="2026-10-23T18:45:00Z",
        )
        clarified_dossier = attach_right_of_reply(
            approved_dossier,
            reply=reply,
            reviewer_id="auditor_chefe_01",
            reclassify_as_clarified=True,
            timestamp_utc="2026-10-23T19:00:00Z",
        )
        storage.upsert_dossier(clarified_dossier, actor_id="auditor_chefe_01")

        # 8. Verificação de visibilidade pós-aprovação
        public_after = storage.list_dossiers_for_role(AccessRole.PUBLIC_READER)
        admin_after = storage.list_dossiers_for_role(AccessRole.REVIEWER_ADMIN)

        output["audit_governance_summary"] = {
            "status": "SUCCESS",
            "dossier_id": clarified_dossier.dossier_id,
            "signal_rule_code": signal.rule_code,
            "signal_metric": signal.metric_name,
            "signal_metric_value": str(signal.metric_value),
            "laya_engine_id": laya_decision.engine_id,
            "laya_score": str(laya_decision.score),
            "laya_action": laya_decision.choice.value,
            "unreviewed_public_dossiers_count": len(public_before),
            "unreviewed_admin_dossiers_count": len(admin_before),
            "published_public_dossiers_count": len(public_after),
            "published_admin_dossiers_count": len(admin_after),
            "final_dossier_status": clarified_dossier.status.value,
            "right_of_reply_protocol": reply.protocol_id,
            "right_of_reply_equal_prominence": reply.equal_visual_prominence,
        }
        output["lakehouse_summary"] = storage.get_summary_metrics()

    print(json.dumps(output, indent=2, ensure_ascii=False))

    if verify_reconciliation and not all(r.is_reconciled for r in reports):
        print("ERRO DE RECONCILIAÇÃO: Totais calculados divergem do controle!", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="donb-ingest",
        description="CLI de Ingestão, Proveniência e Reconciliação — De Olho no Brasil",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample_cmd = subparsers.add_parser(
        "run-sample",
        help="Executa o fluxo completo de dados (4 conectores federais) com reconciliação e quarentena.",
    )
    sample_cmd.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Diretório base do Data Lakehouse (Raw, Quarantine, Curated).",
    )
    sample_cmd.add_argument(
        "--verify-reconciliation",
        action="store_true",
        help="Falha com código de saída != 0 se houver divergência contábil.",
    )
    sample_cmd.add_argument(
        "--run-audit",
        action="store_true",
        help="Executa auditoria determinística, triagem Laya System 1 e governança editorial RLS.",
    )

    audit_cmd = subparsers.add_parser(
        "run-audit",
        help="Executa o fluxo completo incluindo regras de auditoria, triagem Laya e governança editorial.",
    )
    audit_cmd.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Diretório base do Data Lakehouse (Raw, Quarantine, Curated).",
    )
    audit_cmd.add_argument(
        "--verify-reconciliation",
        action="store_true",
        help="Falha com código de saída != 0 se houver divergência contábil.",
    )

    args = parser.parse_args(argv)
    if args.command in ("run-sample", "run-audit"):
        run_audit = getattr(args, "run_audit", False) or (args.command == "run-audit")
        return run_sample_pipeline(
            data_dir=args.data_dir,
            verify_reconciliation=args.verify_reconciliation,
            run_audit=run_audit,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Narrador RAG aterrado (Grounded RAG) e divisão em 3 camadas epistêmicas obrigatórias.

Implementa os requisitos das Seções 7.6, 11 e 12.1:
- GroundedDossierSection: container imutável dos 3 blocos epistêmicos:
  1. [DADO OFICIAL] - fatos extraídos de registros primários auditáveis.
  2. [INFERÊNCIA ESTATÍSTICA] - derivações matemáticas, Z-Score, HHI e score do System 1.
  3. [HIPÓTESE DE AUDITORIA / LIMITAÇÃO] - limitações de escopo, hipóteses analíticas e presunção de boa-fé.
- GroundedDossierNarrator: gerador determinístico ancorado que higieniza textos contra prompt injection,
  rejeita emissão sem hash de proveniência e valida ausência total de termos acusatórios.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from deolhonobrasil.audit.laya_engine import System1Decision
from deolhonobrasil.audit.rules import AuditSignal
from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.privacy import sanitize_untrusted_public_text


@dataclass(frozen=True, slots=True)
class GroundedDossierSection:
    """Seção editorial estruturada nas 3 camadas epistêmicas obrigatórias."""

    official_data_block: str
    statistical_inference_block: str
    audit_hypothesis_and_limits_block: str
    cited_sha256_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.cited_sha256_hashes:
            raise ValueError("A seção editorial exige ao menos um hash de proveniência auditável.")

        if not isinstance(self.cited_sha256_hashes, tuple):
            object.__setattr__(self, "cited_sha256_hashes", tuple(self.cited_sha256_hashes))

        # Verificação rigorosa contra termos acusatórios (Seção 12.1)
        assert_non_accusatory_language(self.official_data_block)
        assert_non_accusatory_language(self.statistical_inference_block)
        assert_non_accusatory_language(self.audit_hypothesis_and_limits_block)


class GroundedDossierNarrator:
    """Gerador determinístico ancorado de narrativas em 3 blocos epistêmicos."""

    def generate(
        self,
        signal: AuditSignal,
        decision: System1Decision,
    ) -> GroundedDossierSection:
        """Gera a narrativa editorial a partir de um sinal de auditoria e de uma decisão do System 1.

        Raises:
            ValueError: Se o sinal não contiver hashes de proveniência ou violar a política editorial.
        """
        if not signal.provenance_hashes:
            raise ValueError(
                "Geração de dossiê recusada: o sinal de auditoria não possui hashes de proveniência (custódia vazia)."
            )

        # Higienização contra ataques de injeção indireta (Indirect Prompt Injection)
        clean_title = sanitize_untrusted_public_text(signal.title, max_length=200)
        clean_fact = sanitize_untrusted_public_text(signal.official_fact_summary, max_length=1500)
        clean_stat = sanitize_untrusted_public_text(signal.statistical_inference_summary, max_length=1500)
        clean_limit = sanitize_untrusted_public_text(signal.scope_limitation_summary, max_length=1500)
        clean_rationale = sanitize_untrusted_public_text(decision.rationale_pt_br, max_length=1000)

        hashes_preview = ", ".join(h[:12] for h in signal.provenance_hashes)

        # Bloco 1: [DADO OFICIAL]
        official_block = (
            f"[DADO OFICIAL] {clean_title}. {clean_fact} "
            f"Montante auditado: R$ {signal.audited_amount:.2f}. "
            f"Registro rastreado nas fontes governamentais sob as chaves de custódia: [{hashes_preview}]."
        )

        # Bloco 2: [INFERÊNCIA ESTATÍSTICA]
        statistical_block = (
            f"[INFERÊNCIA ESTATÍSTICA] {clean_stat} "
            f"Métrica monitorada '{signal.metric_name}': valor apurado de {signal.metric_value} "
            f"(limiar de corte de referência: {signal.threshold_value}). "
            f"Triagem automatizada ({decision.engine_id}): score calibrado em {decision.score:.2f} "
            f"com classificação '{decision.noul_classification}'. Ação de triagem: {decision.choice.value}. "
            f"{clean_rationale}"
        )

        # Bloco 3: [HIPÓTESE DE AUDITORIA / LIMITAÇÃO]
        hypothesis_block = (
            f"[HIPÓTESE DE AUDITORIA / LIMITAÇÃO] {clean_limit} "
            "Este conteúdo reflete uma hipótese analítica gerada por modelos computacionais e "
            "não imputa qualquer conduta ilícita, dolo ou má-fé aos agentes ou fornecedores citados. "
            "A apuração conclusiva depende de auditoria in loco, análise contratual e do exercício regular "
            "do contraditório e da ampla defesa pelos órgãos competentes."
        )

        # Checagem final de segurança da linguagem
        assert_non_accusatory_language(official_block)
        assert_non_accusatory_language(statistical_block)
        assert_non_accusatory_language(hypothesis_block)

        return GroundedDossierSection(
            official_data_block=official_block,
            statistical_inference_block=statistical_block,
            audit_hypothesis_and_limits_block=hypothesis_block,
            cited_sha256_hashes=signal.provenance_hashes,
        )

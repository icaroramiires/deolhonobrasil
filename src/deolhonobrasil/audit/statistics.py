"""Módulo de estatística paramétrica e não-paramétrica para auditoria cívica.

Implementa os detectores descritos na Fase 4:
- Z-Score paramétrico com precisão Decimal exata.
- Z-Score modificado não-paramétrico via Desvio Absoluto Mediano (MAD).
- Índice de Concentração Herfindahl-Hirschman (HHI) para contratações públicas.
- Verificação da Lei de Benford para detecção de anomalias no primeiro dígito.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal, ROUND_HALF_UP

_FIRST_DIGIT_RE = re.compile(r"[1-9]")


def calculate_z_score(value: Decimal, population: Sequence[Decimal]) -> Decimal:
    """Calcula o Z-score paramétrico amostral de um valor frente a uma população de referência.

    Fórmula: Z = (x - mu) / s
    Onde s é o desvio padrão amostral com (N - 1) graus de liberdade.

    Raises:
        ValueError: Se a população contiver menos de 2 elementos ou o desvio padrão for zero.
    """
    if len(population) < 2:
        raise ValueError(
            f"A população para cálculo de Z-score requer no mínimo 2 observações (recebido: {len(population)})."
        )

    val = Decimal(str(value))
    pop = [Decimal(str(x)) for x in population]
    n = Decimal(len(pop))

    mean = sum(pop) / n
    sum_squared_diff = sum((x - mean) ** 2 for x in pop)
    variance = sum_squared_diff / (n - Decimal(1))

    if variance <= Decimal("0"):
        raise ValueError("Desvio padrão da população é zero; distribuição sem variância.")

    std_dev = variance.sqrt()
    if std_dev == Decimal("0"):
        raise ValueError("Desvio padrão da população é zero; impossível calcular Z-Score.")

    z_score = (val - mean) / std_dev
    return z_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_mad_z_score(value: Decimal, population: Sequence[Decimal]) -> Decimal:
    """Calcula o Z-score modificado não-paramétrico via Desvio Absoluto Mediano (MAD).

    Fórmula: M_i = 0.6745 * |x - median| / MAD
    Onde MAD = median(|x_i - median|)

    Recomendado para amostras pequenas ou assimétricas com presença de valores extremos.

    Raises:
        ValueError: Se a população contiver menos de 2 elementos ou MAD for zero.
    """
    if len(population) < 2:
        raise ValueError(
            f"A população para cálculo de MAD Z-score requer no mínimo 2 observações (recebido: {len(population)})."
        )

    val = Decimal(str(value))
    pop = sorted(Decimal(str(x)) for x in population)
    n = len(pop)

    if n % 2 == 1:
        median = pop[n // 2]
    else:
        median = (pop[n // 2 - 1] + pop[n // 2]) / Decimal(2)

    abs_deviations = sorted(abs(x - median) for x in pop)
    if n % 2 == 1:
        mad = abs_deviations[n // 2]
    else:
        mad = (abs_deviations[n // 2 - 1] + abs_deviations[n // 2]) / Decimal(2)

    if mad == Decimal("0"):
        raise ValueError("Desvio Absoluto Mediano (MAD) é zero; distribuição sem dispersão em torno da mediana.")

    # Fator de escala 0.6745 para consistência com a distribuição normal
    mad_z = (Decimal("0.6745") * abs(val - median)) / mad
    return mad_z.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_hhi_concentration(shares_by_supplier: Mapping[str, Decimal]) -> tuple[Decimal, str]:
    """Calcula o Índice de Concentração Herfindahl-Hirschman (HHI) na escala de 0 a 10.000.

    Fórmula: HHI = sum((share_i * 100)^2)

    Classificações:
    - HHI < 1500: 'BAIXA_CONCENTRACAO'
    - 1500 <= HHI <= 2500: 'MODERADA_CONCENTRACAO'
    - HHI > 2500: 'ALTA_CONCENTRACAO'
    """
    if not shares_by_supplier:
        return Decimal("0.00"), "BAIXA_CONCENTRACAO"

    clean_shares: dict[str, Decimal] = {}
    for supplier, share in shares_by_supplier.items():
        val = Decimal(str(share))
        if val > Decimal("0"):
            clean_shares[supplier] = val

    if not clean_shares:
        return Decimal("0.00"), "BAIXA_CONCENTRACAO"

    total = sum(clean_shares.values())
    if total <= Decimal("0"):
        return Decimal("0.00"), "BAIXA_CONCENTRACAO"

    # Se as participações já somam aproximadamente 1 (ex: frações decimais 0.40, 0.60)
    if total <= Decimal("1.0001"):
        hhi = sum((share * Decimal("100")) ** 2 for share in clean_shares.values())
    else:
        # Se foram passados valores monetários absolutos ou percentuais que não somam 1
        hhi = sum(((share / total) * Decimal("100")) ** 2 for share in clean_shares.values())

    hhi_score = hhi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if hhi_score < Decimal("1500.00"):
        classification = "BAIXA_CONCENTRACAO"
    elif hhi_score <= Decimal("2500.00"):
        classification = "MODERADA_CONCENTRACAO"
    else:
        classification = "ALTA_CONCENTRACAO"

    return hhi_score, classification


def evaluate_benford_first_digit(amounts: Sequence[Decimal]) -> dict[str, object]:
    """Avalia a conformidade de uma distribuição de despesas com a Lei de Benford (primeiro dígito).

    P(d) = log10(1 + 1/d) para d em 1..9.
    Calcula:
    - Contagens e frequências observadas vs teóricas
    - Desvio Médio Absoluto (MAD)
    - Estatística Qui-Quadrado (Chi-Square)

    Raises:
        ValueError: Se nenhum valor estritamente positivo for fornecido.
    """
    digits_found: list[int] = []
    for raw in amounts:
        amt = Decimal(str(raw))
        if amt <= Decimal("0"):
            continue
        # Busca o primeiro algarismo não-nulo
        match = _FIRST_DIGIT_RE.search(str(amt))
        if match:
            digits_found.append(int(match.group(0)))

    sample_size = len(digits_found)
    if sample_size == 0:
        raise ValueError("Nenhum valor estritamente positivo encontrado para avaliação de Benford.")

    counts = Counter(digits_found)
    observed_counts: dict[int, int] = {d: counts.get(d, 0) for d in range(1, 10)}

    observed_dist: dict[int, Decimal] = {}
    theoretical_dist: dict[int, Decimal] = {}
    abs_diffs: list[Decimal] = []
    chi_square_acc = Decimal("0.0")

    for d in range(1, 10):
        # P(d) = log10(1 + 1/d)
        p_d_float = math.log10(1.0 + (1.0 / d))
        p_d = Decimal(str(p_d_float)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
        theoretical_dist[d] = p_d

        obs_count = Decimal(observed_counts[d])
        obs_freq = (obs_count / Decimal(sample_size)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
        observed_dist[d] = obs_freq

        diff = abs(obs_freq - p_d)
        abs_diffs.append(diff)

        expected_count = Decimal(sample_size) * p_d
        if expected_count > Decimal("0"):
            term = ((obs_count - expected_count) ** 2) / expected_count
            chi_square_acc += term

    mad = (sum(abs_diffs) / Decimal("9")).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
    chi_square = chi_square_acc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Critérios de conformidade de Nigrini para MAD de primeiro dígito:
    # <= 0.006: Estreita conformidade
    # 0.006 - 0.012: Conformidade aceitável
    # 0.012 - 0.015: Conformidade marginal
    # > 0.015: Não conforme
    if mad <= Decimal("0.00600"):
        assessment = "ESTREITA_CONFORMIDADE"
    elif mad <= Decimal("0.01200"):
        assessment = "CONFORMIDADE_ACEITAVEL"
    elif mad <= Decimal("0.01500"):
        assessment = "CONFORMIDADE_MARGINAL"
    else:
        assessment = "NAO_CONFORME"

    return {
        "sample_size": sample_size,
        "observed_counts": observed_counts,
        "observed_distribution": observed_dist,
        "theoretical_distribution": theoretical_dist,
        "mad": mad,
        "mean_absolute_deviation": mad,
        "chi_square": chi_square,
        "chi_square_statistic": chi_square,
        "is_conformant": mad <= Decimal("0.01500"),
        "conformity_assessment": assessment,
    }

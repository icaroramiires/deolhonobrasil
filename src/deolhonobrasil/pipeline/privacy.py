"""Utilitários de privacidade (LGPD), validação de documentos (CNPJ/CPF), sanitização e SHA-256.

Implementa as regras da Seção 10, 11 e 12.3:
- Minimização de dados pessoais: CPFs de pessoas físicas comuns são mascarados (***.XXX.XXX-**).
- CNPJs (14 dígitos) são normalizados e validados matematicamente pelos dígitos verificadores.
- Textos oriundos de fontes externas são higienizados contra caracteres de controle e tags de prompt injection.
- Valores monetários ausentes NUNCA são convertidos silenciosamente em zero.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation

_DIGITS_ONLY_RE = re.compile(r"\D+")
_MASKED_CPF_PATTERN = re.compile(r"^\*{3}\.?\d{3}\.?\d{3}-?\*{2}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def compute_sha256_bytes(payload: bytes) -> str:
    """Calcula o hash criptográfico SHA-256 hexadecimal de um payload em bytes."""
    return hashlib.sha256(payload).hexdigest()


def compute_sha256_text(text: str, encoding: str = "utf-8") -> str:
    """Calcula o hash criptográfico SHA-256 hexadecimal de uma string."""
    return compute_sha256_bytes(text.encode(encoding))


def validate_cnpj(cnpj_raw: str) -> bool:
    """Valida matematicamente os dígitos verificadores de um CNPJ de 14 dígitos."""
    digits = _DIGITS_ONLY_RE.sub("", cnpj_raw or "")
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_second = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    sum_first = sum(int(d) * w for d, w in zip(digits[:12], weights_first, strict=True))
    rem_first = sum_first % 11
    check_first = 0 if rem_first < 2 else 11 - rem_first
    if int(digits[12]) != check_first:
        return False

    sum_second = sum(int(d) * w for d, w in zip(digits[:13], weights_second, strict=True))
    rem_second = sum_second % 11
    check_second = 0 if rem_second < 2 else 11 - rem_second
    return int(digits[13]) == check_second


def validate_cpf(cpf_raw: str) -> bool:
    """Valida matematicamente os dígitos verificadores de um CPF de 11 dígitos."""
    digits = _DIGITS_ONLY_RE.sub("", cpf_raw or "")
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    sum_first = sum(int(digits[i]) * (10 - i) for i in range(9))
    check_first = (sum_first * 10 % 11) % 10
    if int(digits[9]) != check_first:
        return False

    sum_second = sum(int(digits[i]) * (11 - i) for i in range(10))
    check_second = (sum_second * 10 % 11) % 10
    return int(digits[10]) == check_second


_FREE_TEXT_CPF_RE = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")


def mask_cpf_in_free_text(text: str) -> str:
    """Mascara CPFs válidos encontrados em texto livre, preservando os 6 dígitos centrais."""

    def _replace(match: re.Match[str]) -> str:
        digits = "".join(match.groups())
        if validate_cpf(digits):
            return f"***.{digits[3:6]}.{digits[6:9]}-**"
        return match.group(0)

    return _FREE_TEXT_CPF_RE.sub(_replace, text or "")


def normalize_and_protect_document(raw_doc: str) -> tuple[str, str]:
    """Normaliza um identificador de fornecedor/favorecido aplicando minimização LGPD.

    Retorna uma tupla (documento_normalizado, tipo_documento):
    - 'CNPJ': 14 dígitos puros se for um CNPJ válido.
    - 'CPF_MASKED': formato '***.XXX.XXX-**' para proteger dados pessoais de PF (LGPD).
    - 'EXTERNAL_OR_INVALID': caso inválido ou identificador estrangeiro.
    """
    cleaned = (raw_doc or "").strip()
    if not cleaned:
        raise ValueError("Identificador de documento (CNPJ/CPF) ausente ou vazio.")

    # Caso já venha mascarado da CGU (ex: ***123456** ou ***.123.456-**)
    if _MASKED_CPF_PATTERN.match(cleaned):
        mid_digits = _DIGITS_ONLY_RE.sub("", cleaned)
        if len(mid_digits) == 6:
            return f"***.{mid_digits[:3]}.{mid_digits[3:]}-**", "CPF_MASKED"

    digits = _DIGITS_ONLY_RE.sub("", cleaned)
    if len(digits) == 14:
        if not validate_cnpj(digits):
            raise ValueError(f"CNPJ inválido nos dígitos verificadores: {raw_doc}")
        return digits, "CNPJ"

    if len(digits) == 11:
        if not validate_cpf(digits):
            raise ValueError(f"CPF inválido nos dígitos verificadores: {raw_doc}")
        # Minimização LGPD obrigatória: preserva apenas os 6 dígitos centrais
        return f"***.{digits[3:6]}.{digits[6:9]}-**", "CPF_MASKED"

    raise ValueError(f"Formato de documento não reconhecido (esperado CNPJ 14 ou CPF 11): {raw_doc}")


def parse_strict_monetary_value(raw_value: str | int | float | Decimal | None, field_name: str) -> Decimal:
    """Converte valor monetário com precisão Decimal exata.

    Regra da Seção 10: Dados ausentes NUNCA devem ser tratados silenciosamente como zero.
    Suporta padrão brasileiro ('1.234,56') e internacional ('1234.56').
    """
    if raw_value is None:
        raise ValueError(
            f"Campo monetário obrigatório '{field_name}' está ausente (None). "
            "Proibido converter dado ausente em zero."
        )

    if isinstance(raw_value, Decimal):
        return raw_value.quantize(Decimal("0.01"))

    if isinstance(raw_value, (int, float)):
        return Decimal(str(raw_value)).quantize(Decimal("0.01"))

    text = str(raw_value).strip()
    if not text or text.upper() in {"NULL", "NONE", "N/A", "NA", "-"}:
        raise ValueError(
            f"Campo monetário '{field_name}' está vazio ou nulo ('{raw_value}'). "
            "Proibido converter dado ausente em zero."
        )

    # Remover símbolo de moeda se presente
    text = text.replace("R$", "").strip()

    # Se possui vírgula como separador decimal (padrão BR: 1.234,56 ou 1234,56)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        val = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido em '{field_name}': '{raw_value}'") from exc

    return val.quantize(Decimal("0.01"))


def sanitize_untrusted_text(raw_text: str | None, max_length: int = 2000) -> str:
    """Higieniza texto proveniente de documentos ou APIs externas (Seção 11).

    Remove caracteres de controle invisíveis e neutraliza delimitadores de prompt injection.
    """
    if raw_text is None:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub(" ", str(raw_text))
    # Neutralizar tentativas de fechar tags XML de isolamento ou injetar diretivas de sistema
    cleaned = cleaned.replace("</untrusted_document_data>", "[TAG_REMOVIDA]")
    cleaned = cleaned.replace("<untrusted_document_data>", "[TAG_REMOVIDA]")
    cleaned = re.sub(
        r"ignore\s+all\s+previous\s+instructions",
        "[TAG_REMOVIDA]",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_length]


sanitize_untrusted_public_text = sanitize_untrusted_text


# Data Model & API Contracts — SPEC-0013

## CuratedCorporateMemberRecord
```python
@dataclass(frozen=True)
class CuratedCorporateMemberRecord:
    cnpj: str
    partner_name: str
    masked_cpf: str
    qualification_code: str
    qualification_description: str
    provenance_hash: str
    source: OfficialSource = OfficialSource.RECEITA_FEDERAL_CNPJ
```

## Audit Signals
- `R-CROSS-Qsa-SHARED-PARTNER`: Emitted when overlapping partners appear across supplier entities under the same contracting organ.
- `R-CROSS-QSA-DONOR-SUPPLIER`: Emitted when a corporate partner/supplier maps to a declared personal electoral donation to the campaign of the contracting mandatary.

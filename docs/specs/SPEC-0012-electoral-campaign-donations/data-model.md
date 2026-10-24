# Data Model & Contracts: SPEC-0012

## `CuratedElectoralDonation` (`DATA-014`)
- `donation_id`: `str`
- `donor_tax_id`: `str` (CNPJ 14 digits or masked CPF `***.XXX.XXX-**`)
- `mandatary_id`: `str`
- `election_year`: `int`
- `amount`: `float`
- `source`: `OfficialSource.TSE_ELEICOES`
- `provenance_hash`: `str` (SHA-256)

## `AuditSignal` Dual Provenance (`FR-027`)
- Emits `CROSS_SOURCE_DIVERGENCE` containing expense SHA-256 and electoral donation SHA-256.

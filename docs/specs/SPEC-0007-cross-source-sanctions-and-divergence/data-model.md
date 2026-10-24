# Data Model Contracts — SPEC-0007

## 1. Python Data Model (`CuratedSanctionRecord`)
```python
@dataclass(frozen=True)
class CuratedSanctionRecord:
    sanction_id: str
    supplier_document: str  # Masked CPF (***.XXX.XXX-**) or full 14-digit CNPJ
    supplier_name: str
    sanction_type: str
    start_date: date
    end_date: Optional[date]
    provenance: ProvenanceMetadata
    payload_sha256: str
    status: str  # 'ACTIVE', 'EXPIRED', 'QUARANTINE'
```

## 2. SQLite / Civic Lakehouse Schema (`curated_sanctions`)
```sql
CREATE TABLE IF NOT EXISTS curated_sanctions (
    sanction_id TEXT PRIMARY KEY,
    supplier_document TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    sanction_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    provenance_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 3. Audit Signal Contract
Signals emitted by `R-CROSS-CEIS-SANCTIONED-SUPPLIER` carry classification `CROSS_SOURCE_DIVERGENCE` and chain both source SHA-256 hashes.

# Data Classification Policy

## Purpose
Defines how NEXUS Corp classifies, handles, and protects data based on sensitivity level.

---

## Classification Levels

### Public
- **Definition**: Information approved for unrestricted external distribution
- **Examples**: Marketing materials, published documentation, press releases, open-source code
- **Handling**: No special handling required
- **Storage**: No encryption required (recommended but not mandatory)
- **Transmission**: No encryption required

### Internal
- **Definition**: Business information not approved for external distribution but not sensitive
- **Examples**: Internal procedures, team wikis, non-sensitive project documents, general IT documentation
- **Handling**: Do not share externally without approval
- **Storage**: Encrypted in transit; at-rest encryption recommended
- **Transmission**: Encrypted in transit (TLS 1.2+)

### Confidential
- **Definition**: Sensitive business information where disclosure would cause harm
- **Examples**: Customer PII, financial data, security audit reports, penetration test results, source code, employee data, compliance reports
- **Handling**: Need-to-know basis only; no sharing without explicit approval
- **Storage**: Encrypted at rest (AES-256) and in transit (TLS 1.2+)
- **Transmission**: Encrypted end-to-end; email requires encryption plugin
- **DLP controls**: Data Loss Prevention monitoring active; alerts on bulk downloads

---

## Retention Periods

| Classification | Retention Period | Disposal Method |
|---------------|-----------------|----------------|
| Public | As required by business | Standard deletion |
| Internal | 3 years after last use | Secure deletion (DoD 5220.22-M) |
| Confidential | 7 years or as required by law | Certified destruction + certificate |

**Legal hold exception**: Data subject to litigation hold is exempt from standard retention periods and must not be deleted until hold is released by Legal.

---

## Data Disposal Requirements

### For Confidential data:
- Digital: DoD 5220.22-M standard (3-pass overwrite) or cryptographic erasure (preferred)
- Physical media: Certificate of destruction required from certified vendor
- Cloud storage: Verify deletion via API and retain deletion confirmation
- Backup tapes: Physical destruction (shredding) or degaussing with certificate

### For Internal and Public data:
- Standard secure deletion (single overwrite sufficient)
- Cloud: Standard delete API is acceptable

---

## Labeling Requirements

All documents and files containing Confidential data must be labeled:
- Documents: Header/footer marking on every page
- Files: Classification in filename (e.g., `security-audit-report-CONFIDENTIAL.pdf`)
- Emails: Subject line must include `[CONFIDENTIAL]` for confidential content
- Data in systems: `data_classification` field populated in all data stores

---

## Responsibility

- **Data Owner**: Business unit that creates or owns the data; responsible for classification
- **Data Custodian**: IT Operations; responsible for technical controls
- **Data Users**: All employees; responsible for following handling requirements
- **CISO**: Responsible for policy enforcement and exception approval

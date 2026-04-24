# Patch Management Policy

## Purpose
This policy defines requirements for patching software vulnerabilities across all NEXUS Corp systems to minimize security risk and maintain compliance.

---

## Patch Classification and SLAs

| Severity | CVSS Score | Patch SLA | Emergency Patch |
|----------|-----------|-----------|----------------|
| Critical | ≥9.0 | **48 hours** | Yes — ECAB required |
| High | 7.0–8.9 | **7 days** | Available if actively exploited |
| Medium | 4.0–6.9 | **30 days** | No |
| Low | <4.0 | **90 days** | No |

**Note**: Actively exploited vulnerabilities (CISA KEV catalog) are treated as Critical regardless of CVSS score.

---

## Standard Patch Procedure

### Testing Requirements
All patches must follow this pipeline:

1. **Development environment**: Apply patch, run smoke tests (minimum 2 hours soak)
2. **Staging environment**: Apply patch, run full regression suite (minimum 24-hour soak for non-critical)
3. **Production canary**: Deploy to 5% of production fleet, monitor for 1 hour
4. **Production rollout**: Deploy remaining production fleet

**Critical patch exception**: May skip canary in emergency, but requires post-deployment monitoring window.

---

## Emergency Out-of-Band Patch Procedure

For Critical vulnerabilities with active exploitation:

1. **Approval**: ECAB (Emergency Change Advisory Board) approval required
   - ECAB: CISO + Engineering Manager + Change Manager
   - Approval turnaround: Maximum **2 hours** from submission
2. **Deployment window**: **4 hours** from approval to complete production deployment
3. **Testing**: Staging only (dev may be skipped for genuine emergencies)
4. **Post-deployment**: Mandatory 1-hour monitoring, incident commander on standby
5. **Documentation**: Full change record closed within 24 hours

---

## Exception Process

When a patch cannot be applied within SLA:

1. Submit exception request to IT Security via ITSM ticket
2. Document: **Why** patch cannot be applied (technical constraint, vendor support)
3. Document: **Compensating controls** implemented to reduce risk (WAF rule, network isolation, enhanced monitoring)
4. **CISO approval required** for any exception
5. Exception valid for: Maximum 30 days, then must re-apply or escalate
6. **No exceptions** for zero-day vulnerabilities with active exploitation

### Risk Acceptance Form
Required fields:
- CVE ID and CVSS score
- Affected systems and data classification
- Business justification for exception
- Compensating controls in place
- Residual risk rating (must be ≤ Medium after compensating controls)
- Review date (max 30 days)
- CISO signature

---

## Patch Compliance KPIs

**Reported weekly via automated dashboard:**

| Metric | Target |
|--------|--------|
| Critical patches within 48h | ≥99% |
| High patches within 7 days | ≥95% |
| Medium patches within 30 days | ≥90% |
| Low patches within 90 days | ≥85% |
| Exceptions currently active | ≤5 |

**Dashboard refresh**: Every 6 hours (automated)
**Weekly report**: Sent to CISO, Engineering Manager, and IT Security every Monday 08:00 UTC

---

## Scope

This policy applies to:
- All servers (virtual and physical) in production, staging, and development
- All containers (base images must be patched before deployment)
- All workstations and laptops (managed via MDM)
- All network devices (switches, routers, firewalls)
- All SaaS applications where patch control is available

**Out of scope**: Vendor-managed SaaS where patching is vendor responsibility (document in CMDB).

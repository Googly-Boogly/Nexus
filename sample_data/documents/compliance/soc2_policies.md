# SOC 2 Type II Compliance Policies

## Overview
This document defines NEXUS Corp's controls for SOC 2 Type II compliance, covering the Trust Services Criteria (TSC) for Security, Availability, and Confidentiality.

---

## CC6 — Logical and Physical Access Controls

### CC6.1 — Logical Access Security Measures

**Password Policy:**
- Minimum length: 12 characters
- Complexity: Must contain uppercase, lowercase, number, and special character
- Maximum age: 90 days (mandatory rotation)
- History: Cannot reuse last 12 passwords
- Failed attempt lockout: 5 failed attempts → 15-minute lockout

**Multi-Factor Authentication (MFA):**
- MFA is required for ALL user accounts accessing production systems
- MFA is required for all VPN connections
- Hardware MFA tokens required for privileged (admin) accounts
- Time-based OTP (TOTP) acceptable for standard accounts
- Exception process: Requires CISO written approval, valid for max 30 days

### CC6.2 — Access Provisioning

Workflow for granting access:
1. Manager submits access request via ITSM ticket
2. IT Security reviews against least-privilege principle
3. IT Operations implements access change
4. Manager verifies access is correct
5. IT Security logs provisioning in CMDB
6. Access review reminder set for 90 days

**Privileged access provisioning** requires an additional approval:
- Approval from IT Security Manager
- Justification must reference specific job function
- Time-limited where possible (max 90 days before re-review)

### CC6.3 — Access Reviews

**Quarterly privileged access review:**
- All accounts with admin or elevated privileges reviewed
- Inactive admin accounts (no login in 30 days): Disable immediately
- Accounts without business justification: Remove within 5 business days
- Review completed by: System owner + IT Security co-review

**Annual standard user access review:**
- All user accounts reviewed against current employee/contractor list
- Terminated employees: Access removed within 1 hour of termination
- Contractors: Access removed on contract end date

---

## CC7 — System Operations

### CC7.1 — Detection of and Monitoring for New Vulnerabilities

**Monitoring requirements:**
- Vulnerability scans: Weekly automated scans on all production assets
- Penetration testing: Annual third-party pentest required
- SIEM monitoring: 24/7 for defined alert thresholds
- IDS/IPS: All ingress/egress traffic monitored

**Alert thresholds requiring immediate response:**
- Failed logins >50/minute per account
- Data exfiltration >1GB in 1 hour
- New admin account created outside change window
- Network traffic to known malicious IPs
- Privilege escalation on production host

### CC7.2 — Monitoring of System Components

**Required monitoring for production systems:**
- CPU utilization: Alert at >80% for 5 minutes
- Memory utilization: Alert at >85% for 5 minutes
- Disk usage: Alert at >80% on all volumes
- Error rate: Alert when >5% of requests error
- Availability: Alert when health check fails for >1 minute

**Log retention:**
- Application logs: 90 days hot, 1 year cold storage
- Access logs: 1 year hot, 3 years cold storage
- Audit logs: 3 years, immutable storage (WORM)
- Security event logs: 3 years, SIEM retention

### CC7.3 — Evaluation of Security Events

Incident SLA by severity:
- Critical/S1: Acknowledge within 15 minutes, contain within 1 hour
- High/S2: Acknowledge within 30 minutes, contain within 4 hours
- Medium/S3: Acknowledge within 4 hours, remediate within 48 hours
- Low/S4: Acknowledge within 1 business day, remediate within 2 weeks

---

## CC8 — Change Management

### CC8.1 — Change Management Process

All production changes must follow this workflow:

1. **Request**: Engineer creates change ticket in ITSM
2. **Review**: Peer review of change plan and rollback procedure
3. **Testing**: Changes must pass all automated tests (CI/CD pipeline)
4. **CAB Approval**:
   - Standard changes: Automatic approval (pre-authorized, low risk)
   - Normal changes: CAB approval required (weekly CAB meeting)
   - Emergency changes: ECAB approval required (< 2 hours)
5. **Implementation**: During approved change window (Tuesday/Thursday 02:00-06:00 UTC)
6. **Validation**: Post-change verification, 30-minute monitoring window
7. **Closure**: Confirm change is successful, close ticket

**Rollback requirement**: Every change must have a documented rollback procedure executable in <15 minutes.

---

## CC9 — Risk Mitigation

### CC9.1 — Risk Management Process

Annual risk assessment required:
- Identify assets and threat vectors
- Rate likelihood and impact (1-5 scale)
- Calculate risk score (likelihood × impact)
- High/Critical risks: Remediation plan within 30 days
- Medium risks: Remediation plan within 90 days
- Low risks: Accept or remediate at next annual review

### CC9.2 — Vendor and Business Partner Management

All vendors with access to production data require:
- SOC 2 Type II report (within 12 months) OR equivalent security certification
- Signed Data Processing Agreement (DPA)
- Annual vendor security questionnaire
- Right-to-audit clause in contract

**Business Continuity Planning (BCP):**
- BCP test required annually
- RTO: 4 hours for critical systems
- RPO: 30 seconds (database), 5 minutes (application)
- BCP documentation must be updated after any significant infrastructure change

---

## Audit Evidence Requirements

For each SOC 2 control, auditors require:
- Policy document (this document, version-controlled)
- System screenshot or configuration export showing control in place
- Sample of control operation (e.g., sample of access requests and approvals)
- Exception log (any deviations from policy and how they were handled)

Evidence must be produced within 3 business days of auditor request.

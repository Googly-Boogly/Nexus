# NIST SP 800-53 Rev 5 Controls Implementation

## Overview
This document maps NEXUS Corp's security controls to NIST SP 800-53 Rev 5. Controls are implemented at the Moderate baseline level.

---

## AC — Access Control

### AC-2: Account Management
**Control**: The organization manages information system accounts.

**Implementation**:
- All accounts are managed through centralized IAM (AWS IAM, Active Directory)
- Account types: user, admin, service, emergency
- Account creation requires manager approval via ITSM ticket
- Account review: Quarterly for privileged, annual for standard
- Dormant account (no login 45 days): Automatic disable
- Terminated employee: Disable within 1 hour, delete within 30 days

**Evidence**: IAM account list, access review records, ITSM provisioning tickets

### AC-6: Least Privilege
**Control**: Employ the principle of least privilege.

**Implementation**:
- All IAM roles follow least-privilege: only permissions required for job function
- Prohibited: AdministratorAccess policy on any service account
- Service accounts: Named, documented, owner assigned, no interactive login
- Admin access: Time-limited, requires justification, re-reviewed every 90 days
- PAM solution: All privileged access via jump server with session recording

**Evidence**: IAM policy analysis report, PAM session logs, privilege review records

### AC-17: Remote Access
**Control**: Establish and document remote access requirements.

**Implementation**:
- All remote access requires VPN (WireGuard/OpenVPN)
- VPN requires MFA (hardware token for privileged users)
- Split tunneling: Disabled — all traffic routes through corporate VPN
- VPN sessions: Maximum 8-hour session, re-authentication required
- Remote desktop: Prohibited except through jump server with session recording

---

## AU — Audit and Accountability

### AU-2: Event Logging
**Control**: Identify the types of events that the system is capable of auditing.

**Audited events**:
- Authentication: Login, logout, failed login, lockout, MFA events
- Authorization: Access granted, access denied, privilege escalation
- Data access: Read of confidential data, data export, data deletion
- System: Service start/stop, configuration changes, software installation
- Network: VPN connect/disconnect, firewall rule changes, unusual traffic patterns

### AU-9: Protection of Audit Information
**Control**: Protect audit information and tools from unauthorized access.

**Implementation**:
- Audit logs stored in immutable S3 bucket (Object Lock, WORM mode)
- Audit logs replicated to secondary region within 15 minutes
- Log integrity: SHA-256 hash of each log file, hash stored separately
- Access to audit logs: Restricted to Security team and auditors
- Row-level security on audit_log table: Users see only their own records

### AU-11: Audit Record Retention
**Control**: Retain audit records for 3 years.

**Implementation**:
- Hot storage (S3 Standard): 90 days
- Warm storage (S3 Intelligent-Tiering): 1 year
- Cold storage (S3 Glacier): 3 years total
- Legal hold: Audit records on litigation hold exempted from deletion

---

## CM — Configuration Management

### CM-2: Baseline Configuration
**Control**: Document and maintain baseline configurations.

**Implementation**:
- All infrastructure defined as code (Terraform, CloudFormation)
- Baseline AMI: Hardened image built from CIS Benchmark Level 2
- Configuration drift detection: Daily scan via AWS Config
- Approved deviations: Documented in CMDB with risk acceptance

### CM-6: Configuration Settings
**Control**: Establish and document configuration settings.

**Required configuration settings for all production systems**:
- SSH: Password authentication disabled, root login disabled, key-based only
- Services: Only required services running, unnecessary ports closed
- Firewall: Default-deny inbound, explicit allow rules only
- Logging: Syslog to central SIEM enabled
- Encryption: TLS 1.2+ for all inter-service communication

### CM-8: System Component Inventory
**Control**: Develop and document an inventory of system components.

- CMDB updated within 24 hours of provisioning or decommissioning
- Auto-discovery scan runs weekly to detect undocumented assets
- Each asset record includes: owner, data classification, environment, last review date

---

## IR — Incident Response

### IR-4: Incident Handling
**Control**: Implement an incident handling capability.

Implementation covers: Preparation, Detection, Analysis, Containment, Eradication, Recovery, Post-incident.
See Incident Response Runbook for detailed procedures.

### IR-6: Incident Reporting
**Control**: Report suspected security incidents.

- All suspected security incidents reported to security@nexus.corp within 1 hour of discovery
- External reporting (if breach): Within 72 hours to regulatory bodies (GDPR DPA)
- Annual incident response exercise/tabletop required

---

## SI — System and Information Integrity

### SI-2: Flaw Remediation
**Control**: Identify, report, and correct information system flaws.

**Patch SLAs** (see Patch Management Policy for full details):
- Critical CVE (CVSS ≥9.0): 48 hours
- High CVE (CVSS 7.0–8.9): 7 days
- Medium CVE (CVSS 4.0–6.9): 30 days
- Low CVE (CVSS <4.0): 90 days

### SI-3: Malware Protection
**Control**: Implement malicious code protection.

- EDR (Endpoint Detection and Response) installed on all endpoints and servers
- Signature updates: Automatic, within 1 hour of vendor release
- Full scan: Weekly, off-peak hours
- Suspicious process detected: Automatic quarantine, alert to SOC

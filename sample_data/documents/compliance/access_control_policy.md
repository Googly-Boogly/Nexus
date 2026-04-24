# Access Control Policy

## Purpose
Defines requirements for controlling access to NEXUS Corp systems, data, and facilities to prevent unauthorized access and enforce least privilege.

---

## Access Provisioning Workflow

1. **Request**: Employee or manager submits access request ticket in ITSM
2. **Manager Approval**: Direct manager approves within 2 business days
3. **IT Implementation**: IT Operations provisions access within 1 business day of approval
4. **Verification**: Requestor confirms access is working and appropriate
5. **CMDB Update**: IT Operations updates access record in CMDB

**For privileged access** (admin, root, DBA):
- Additional approval from IT Security Manager required
- Justification must document specific business need and duration
- Time-limited: Maximum 90 days, then re-review required
- Jump server required for all privileged access

---

## Privileged Access Management (PAM)

### Requirements for Privileged Access
- All privileged access must go through the jump server (bastion host)
- Session recording is **mandatory** for all privileged sessions
- No direct SSH with root credentials — must use named user account then `sudo`
- No shared accounts — every admin must have a personal named account
- Hardware MFA token required for all privileged accounts
- Privileged sessions: Maximum 4-hour duration, re-authentication required

### Service Account Requirements
- Every service account must have a named human owner (documented in CMDB)
- No interactive login for service accounts — disable login shell
- Service account passwords: Rotate every **90 days** via automated tooling
- Service accounts must not have permissions beyond what the service requires
- Service accounts must not have console access (programmatic only)
- Emergency access procedures: Document break-glass procedure for each service account

---

## Access Reviews

### Quarterly Privileged Access Review
- **Who reviews**: System owner and IT Security co-review
- **Scope**: All accounts with admin, root, DBA, or security team permissions
- **Action for stale accounts** (no login in 30 days): Disable within 5 business days
- **Action for unjustified accounts**: Remove access within 5 business days
- **Documented in**: ITSM ticket with reviewer names and date
- **Escalation**: Non-compliance reported to CISO within 10 business days

### Annual Standard User Review
- All active user accounts reviewed against HR system (current employees/contractors)
- Terminated employees: Access disabled within **1 hour** of termination confirmation
- Contractors: Access automatically disabled on contract end date in system
- Transfers: Access review within 30 days to ensure access matches new role

---

## Termination Procedures

### Immediate Actions (within 1 hour of termination)
1. Disable all user accounts (AD, AWS IAM, application accounts)
2. Revoke all active VPN sessions
3. Revoke all API keys and OAuth tokens
4. Disable email account

### Actions within 24 hours
1. Delete or transfer files from user's home directory
2. Remove user from all distribution lists
3. Revoke hardware MFA tokens
4. Update CMDB to reflect account status

### Actions within 30 days
1. Delete all accounts (unless legal hold)
2. Transfer ownership of resources owned by departed employee
3. Audit for any orphaned resources or access paths

---

## Remote Access Requirements

- All remote access requires approved VPN client
- VPN requires MFA — no exceptions
- Split tunneling: Disabled on corporate VPN
- Personal devices: Must meet MDM enrollment requirements before VPN access
- Public Wi-Fi: Must use VPN immediately upon connection
- VPN inactivity timeout: 30 minutes for standard users, 15 minutes for privileged users

# Security Incident Runbook

## Overview
This runbook covers detection, containment, evidence preservation, and recovery for security incidents including unauthorized access, data breaches, malware, and active intrusions.

---

## Severity Classification (Security)

| Severity | Definition | Examples |
|----------|------------|---------|
| S1 | Active breach, data exfiltration in progress, ransomware | Confirmed unauthorized access, active data theft |
| S2 | Potential breach, suspicious admin activity, lateral movement | Unusual login from foreign IP, new admin account created |
| S3 | Policy violation, malware detected (contained) | User downloaded malware, phishing email clicked |
| S4 | Minor policy violation, no data risk | Unauthorized software installed, policy exception |

---

## Detection Sources

Security incidents are typically detected via:
- **SIEM alerts**: Anomaly detection, impossible travel, after-hours logins
- **IDS/IPS**: Signature matches, behavioral anomalies
- **User reports**: "I think I was phished" or "I see strange activity"
- **Threat intel feeds**: Known malicious IPs/domains in firewall logs
- **EDR alerts**: Malware detection, process injection, fileless attacks
- **Application alerts**: Impossible login rates, credential stuffing patterns

---

## Step 1: Initial Containment (S1/S2)

**For active intrusion or data exfiltration:**

### Immediate host isolation
```bash
# AWS: Isolate EC2 instance by modifying security group
aws ec2 modify-instance-attribute \
  --instance-id <instance-id> \
  --groups sg-isolation-only  # SG with no inbound/outbound except management VLAN

# Kubernetes: Remove pod from service (but keep pod alive for forensics)
kubectl label pod <pod-name> app=isolated
kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"quarantine"}}}'
```

### Credential rotation triggers
If credentials are suspected compromised:
1. Immediately rotate: API keys, database passwords, service account credentials
2. Revoke all active sessions for affected users: AWS CLI, Console, application sessions
3. Enable MFA requirement for all remaining admin accounts
4. Review and revoke OAuth tokens for affected applications

### Firewall rules for containment
```bash
# Block outbound traffic to suspicious IP
iptables -I OUTPUT -d <suspicious-ip> -j DROP

# AWS: Add deny rule to NACL
aws ec2 create-network-acl-entry \
  --network-acl-id <acl-id> \
  --rule-number 1 \
  --protocol -1 \
  --rule-action deny \
  --cidr-block <suspicious-ip>/32 \
  --egress
```

---

## Step 2: Evidence Preservation (Chain of Custody)

**Collect before any remediation:**

### Log collection
```bash
# System logs (last 24h)
tar -czf /evidence/syslogs-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/log/auth.log* /var/log/syslog* /var/log/secure*

# Application logs
tar -czf /evidence/applogs-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/log/app/*.log

# Network flow logs (AWS VPC Flow Logs)
aws s3 cp s3://vpc-flow-logs/ /evidence/network-flows/ --recursive
```

### Memory dump (if live analysis needed)
```bash
# Linux memory capture (requires LiME module)
sudo insmod lime.ko "path=/evidence/memory.lime format=lime"

# Alternative: /proc/kcore (partial)
dd if=/proc/kcore of=/evidence/kcore.dump
```

### Forensic image
- Create EBS snapshot BEFORE terminating instance
- Tag snapshot: `forensics=true`, `incident=S1-YYYYMMDD`
- Do NOT boot from snapshot — analyze offline

---

## Step 3: Notification Obligations

### Timeline by severity

| S1 | Action |
|----|--------|
| T+0 | Begin containment |
| T+15 min | Notify CISO and Engineering Manager |
| T+30 min | Notify Legal team |
| T+1 hour | Determine if breach of PII data occurred |
| T+4 hours | If PII breach: notify Data Protection Officer |
| T+72 hours | GDPR breach notification deadline (if applicable) |

| S2 | Action |
|----|--------|
| T+30 min | Notify CISO |
| T+2 hours | Assess if escalation to S1 required |

---

## Step 4: Recovery and Hardening

After containment and investigation:

1. **Rebuild affected systems** from known-good AMI/image — do not restore from potentially compromised image
2. **Patch the exploit vector** before bringing systems back online
3. **Rotate all credentials** that could have been exposed
4. **Review and tighten** access controls: remove all unnecessary permissions
5. **Add detection rules** for the attack pattern used
6. **Re-enable monitoring** and verify alerts fire correctly on test events

---

## Step 5: Post-Incident Requirements

**48-hour RCA required for all S1 and S2 incidents:**
- Timeline of attacker activity (when did they first gain access?)
- Attack vector used (how did they get in?)
- Blast radius (what systems/data were accessible?)
- Data exfiltrated (what was taken, if anything?)
- Remediation steps taken
- Residual risk assessment
- Regulatory notification requirements (GDPR, SOC2 breach notification)

**Lessons learned review within 7 days:**
- What detection controls failed or were missing?
- What response steps were effective/ineffective?
- Updated runbook and security controls

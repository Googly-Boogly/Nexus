# Escalation Matrix

## Overview
Defines escalation paths, time limits, and contact methods for production incidents and support requests.

---

## Escalation Path

| Level | Role | Team | Contact Method | Response Time |
|-------|------|------|----------------|---------------|
| L1 | On-Call Engineer | Platform/SRE | PagerDuty | Acknowledge: 5 min |
| L2 | Platform Lead / Senior SRE | Platform | PagerDuty escalation | Escalate at: L1+15 min |
| L3 | Engineering Manager | Engineering | Direct PagerDuty page + Slack | Escalate at: L2+30 min |
| L4 | VP Engineering | Executive | Phone call | Escalate at: L3+30 min (P1 only) |
| L5 | CISO | Security | Phone call | Security incidents S1/S2 only |

---

## Escalation Time Limits

### P1 Incidents
- **T+0**: L1 acknowledges alert
- **T+5 min**: If not acknowledged → PagerDuty auto-escalates to L2
- **T+15 min**: L1 must have identified root cause or escalated to L2
- **T+30 min**: L2 escalates to L3 if not contained
- **T+60 min**: L3 notifies L4 (VP Engineering)
- **T+2 hours**: Customer-facing status page update required
- **T+4 hours**: SLA breach — executive escalation mandatory

### P2 Incidents
- **T+0**: L1 acknowledges alert
- **T+15 min**: L1 begins active investigation
- **T+30 min**: Escalate to L2 if root cause unknown
- **T+2 hours**: L2 escalates to L3 if not resolved
- **T+8 hours**: SLA breach — manager notification required

---

## Contact Channels

| Severity | Primary | Secondary | Bridge |
|----------|---------|-----------|--------|
| P1 | PagerDuty (auto-page) | Slack #incidents (real-time) | Zoom bridge (auto-created) |
| P2 | PagerDuty | Slack #incidents | On request |
| P3 | Slack #ops-alerts | ITSM ticket | N/A |
| P4 | ITSM ticket | N/A | N/A |

**Business hours**: Monday–Friday 09:00–18:00 local time (all escalation paths available)
**After hours**: P1/P2 only via PagerDuty; P3/P4 next business day

---

## Security Incident Escalation

| Step | Who | When |
|------|-----|------|
| Initial containment | On-Call Engineer | Immediately |
| Notify Security Team | IT Security | T+15 min |
| Notify CISO | L5 | T+30 min (S1/S2) |
| Notify Legal | L5 initiates | T+1 hour if data at risk |
| Customer notification | Communications team | As directed by Legal/CISO |

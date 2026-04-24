# Incident Response Runbook v2.1

## Purpose
This runbook defines the standard procedures for identifying, classifying, containing, and resolving production incidents at NEXUS Corp. All on-call engineers and SREs must follow these procedures for every incident.

---

## Severity Classification

| Severity | Definition | SLA: Acknowledge | SLA: Contain | SLA: Resolve |
|----------|------------|-----------------|--------------|--------------|
| P1 | Complete service outage or data loss risk affecting >1000 customers | 5 minutes | 1 hour | 4 hours |
| P2 | Degraded service affecting >100 customers or a critical subsystem | 15 minutes | 2 hours | 8 hours |
| P3 | Minor degradation affecting <100 customers, workaround available | 30 minutes | 4 hours | 24 hours |
| P4 | Cosmetic issue or low-impact bug, no customer impact | 4 hours | Next business day | 72 hours |

---

## First Response Checklist

Upon receiving an alert, the on-call engineer must:

1. **Acknowledge the page** within the SLA window (PagerDuty: click "Acknowledge")
2. **Assess impact**: How many customers are affected? Which services are down?
3. **Classify severity**: Use the table above. When in doubt, escalate up.
4. **Declare incident**: For P1/P2, immediately create an incident channel `#inc-YYYYMMDD-NNN`
5. **Post initial update** in channel: "Incident declared. Investigating. ETA for update: X minutes."
6. **Begin investigation**: Check system dashboards, logs, and recent deployments
7. **Communicate immediately** for P1: Notify on-call manager within 10 minutes

---

## Escalation Decision Tree

```
Alert received
    │
    ├─ Is service completely unavailable? → YES → P1 → Immediate page
    │                                        NO ↓
    ├─ Are >100 customers impacted? → YES → P2 → Page within 15 min
    │                                  NO ↓
    ├─ Is there a workaround? → YES → P3 → Create ticket
    │                            NO → P2 → Escalate
    └─ All else → P4 → Create ticket, next sprint
```

### Escalation Contacts

| Level | Role | Contact | Hours |
|-------|------|---------|-------|
| L1 | On-call Engineer | PagerDuty rotation | 24/7 |
| L2 | Platform Lead | PagerDuty escalation policy | 24/7 |
| L3 | Engineering Manager | Direct page + Slack | 24/7 for P1 |
| L4 | VP Engineering | Phone call | P1 only, 30+ min unresolved |
| L5 | CISO | Phone call | Security incidents only |

### Time Limits
- **L1 → L2 escalation**: If L1 has not contained within 15 minutes of a P1
- **L2 → L3 escalation**: If L2 has not contained within 30 minutes of a P1
- **L3 → L4 notification**: If P1 is unresolved at 1 hour

---

## Service Restart Procedure

### Pre-restart checklist
1. Verify the service is actually unhealthy: `systemctl status <service>` or `kubectl get pods`
2. Capture current logs: `journalctl -u <service> --since "10 min ago" > /tmp/pre-restart.log`
3. Check for active connections: `ss -tnp | grep <port>`
4. Notify in incident channel: "Restarting <service> on <host> at HH:MM UTC"

### Restart steps
```bash
# For systemd services
sudo systemctl restart <service-name>
sleep 10
systemctl status <service-name>

# For Kubernetes
kubectl rollout restart deployment/<deployment-name> -n <namespace>
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

### Post-restart verification
1. Confirm service reports healthy: `curl -sf http://localhost:<port>/health`
2. Check error rate in Grafana: should return to baseline within 2 minutes
3. Verify no new errors in logs: `journalctl -u <service> --since "2 min ago" | grep ERROR`
4. Post in incident channel: "Service restarted. Status: healthy. Monitoring for 5 minutes."

---

## Stakeholder Communication Templates

### Initial notification (P1/P2, within SLA)
```
INCIDENT NOTIFICATION — [SEVERITY]
Time: [HH:MM UTC]
Status: INVESTIGATING
Impact: [Brief description of customer impact]
Services affected: [List]
Next update: [Time, max 30 min]
Incident channel: #inc-[YYYYMMDD-NNN]
```

### Update (every 30 minutes for P1, every hour for P2)
```
INCIDENT UPDATE — [SEVERITY] [INC-XXXXX]
Time: [HH:MM UTC]
Status: [INVESTIGATING | IDENTIFIED | MITIGATING | MONITORING]
Progress: [What has been done, what is in progress]
Root cause: [If known, or "Under investigation"]
ETA to resolution: [Best estimate or "Unknown"]
Next update: [Time]
```

### Resolution notification
```
INCIDENT RESOLVED — [SEVERITY] [INC-XXXXX]
Resolution time: [HH:MM UTC]
Duration: [X hours Y minutes]
Root cause: [Brief RCA]
Fix applied: [Description]
Customers affected: [Count or estimate]
Post-incident review: [Scheduled date/time]
```

---

## Post-Incident Review (PIR)

**Required for**: All P1 and P2 incidents.

### PIR must be completed within:
- P1: 24 hours post-resolution
- P2: 72 hours post-resolution

### PIR document must include:
1. Timeline of events (when alert fired, when acknowledged, key actions, resolution)
2. Root cause analysis (5 Whys or fishbone diagram)
3. Contributing factors
4. What went well
5. What could be improved
6. Action items with owners and due dates (max 5 action items)

### PIR format
All PIRs must be blameless. No individual is blamed. Focus on systems and processes.

Post PIR document to: `#post-incident-reviews` Slack channel and Confluence space `/Engineering/PIR`

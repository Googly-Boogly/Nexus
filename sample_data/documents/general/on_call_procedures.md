# On-Call Procedures

## Schedule and Coverage

- **Rotation**: 1-week rotation, Monday 09:00 → following Monday 09:00 UTC
- **Coverage requirement**: 24/7 for all P1/P2 alerts
- **Minimum staffing**: 1 primary + 1 secondary (backup) on-call at all times
- **Rotation tool**: PagerDuty (primary), with Slack integration for awareness

---

## Response SLA

All on-call engineers must:
- **Acknowledge** PagerDuty page within **5 minutes** at any time of day/night
- **Begin investigation** within 15 minutes of acknowledgement
- **Post initial update** in incident channel within 10 minutes of acknowledgement
- **Escalate** to secondary on-call if unable to investigate within 15 minutes

If you cannot respond (medical emergency, etc.), notify secondary immediately via phone.

---

## Handoff Checklist

At the end of each on-call week, outgoing on-call must brief incoming on-call:

### Required items in handoff document
- [ ] **Open incidents**: List all P1/P2 incidents still open; status and next actions
- [ ] **Known issues**: Any production issues being monitored but not yet incidents
- [ ] **Recent deployments**: All production changes in the last 24 hours and their status
- [ ] **Upcoming scheduled events**: Planned maintenance, deployments, capacity changes in next 7 days
- [ ] **System health notes**: Any systems running degraded or requiring extra monitoring
- [ ] **Alert fatigue items**: Any alerts currently suppressed or in maintenance mode

Handoff meeting: 30 minutes, Thursday before rotation end

---

## On-Call Best Practices

**During incidents**:
1. Think out loud — post your investigation steps in the incident channel
2. Ask for help early — escalating is not a sign of weakness
3. Document everything — future you will thank present you
4. Take breaks during long incidents — ask for a second person to take over if >4 hours

**After incidents**:
- All P1/P2 incidents require a blameless postmortem (see IR Runbook)
- Write up "near misses" — issues caught before they became incidents
- Suggest alert threshold improvements if you got paged for something non-actionable

---

## Postmortem Requirements

| Severity | PIR Required | Deadline | Author |
|----------|-------------|----------|--------|
| P1 | Yes | 24 hours | On-call engineer who resolved |
| P2 | Yes | 72 hours | On-call engineer who resolved |
| P3 | Optional (recommended for recurring) | 1 week | Team lead |
| P4 | No | — | — |

PIR template is in Confluence: Engineering → Post-Incident Reviews → Template
All PIRs reviewed in weekly engineering all-hands.

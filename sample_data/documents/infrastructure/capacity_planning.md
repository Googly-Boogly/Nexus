# Capacity Planning Guide

## Overview
This document defines the process and policies for capacity planning across NEXUS Corp's cloud infrastructure.

---

## Review Cadence

| Review Type | Frequency | Owner | Audience |
|-------------|-----------|-------|----------|
| Utilization review | Monthly | Platform Team | Engineering leads |
| Forecast review | Quarterly | Platform Team + Finance | VP Engineering, CFO |
| Annual planning | Annually | Platform + Finance | C-suite |

---

## Headroom Target

**Policy**: Always maintain **20% capacity headroom** above forecasted peak load.

This means:
- If peak CPU utilization is 70%, target infrastructure can handle 87.5% (70 / 0.8)
- If peak requests/second is 1000, ensure infrastructure handles 1250 req/s before scaling

Headroom protects against:
- Unexpected traffic spikes (viral events, bot traffic)
- Degraded nodes during rolling deployments
- Hardware failures requiring redistribution of load

---

## Auto-Scaling Policies

### Scale-Out (Add Capacity)
| Metric | Threshold | Duration | Action |
|--------|-----------|----------|--------|
| CPU Utilization | >70% | 5 minutes sustained | Add 2 instances |
| Request Count | >80% of current capacity | 2 minutes | Add 2 instances |
| Memory Utilization | >75% | 5 minutes | Add 2 instances |
| Queue Depth (SQS) | >1000 messages | Immediate | Add 4 workers |

**Cooldown period**: 5 minutes between scale-out actions (prevents oscillation)

### Scale-In (Remove Capacity)
| Metric | Threshold | Duration | Action |
|--------|-----------|----------|--------|
| CPU Utilization | <30% | 15 minutes sustained | Remove 1 instance |
| Request Count | <40% of current capacity | 15 minutes | Remove 1 instance |

**Scale-in protection**: Never scale below minimum instance count (defined per service, typically 2 for HA)

---

## Reserved Instance Strategy

**Baseline load** (consistent 24/7 traffic): Use 1-year Reserved Instances (RI)
- Savings: ~40% vs On-Demand
- Commitment: 1 year (no upfront recommended for flexibility)
- Coverage target: 70% of average utilization

**Burst capacity** (above baseline): Use On-Demand
- No commitment required
- Pay-per-use for spikes

**Scheduled capacity** (predictable spikes): Use Scheduled Scaling
- Configure scale-out 15 minutes before expected spike
- Example: Scale up database read replicas before month-end batch jobs

---

## Cost Anomaly Detection

**Automated alerts** via AWS Cost Anomaly Detection:
- **15% MoM increase**: Email alert to Engineering Manager and Finance
- **30% MoM increase**: Page on-call platform engineer
- **50% MoM increase**: Immediate investigation required, escalate to VP Engineering

**Response to cost anomalies**:
1. Identify the resource or service causing the increase
2. Determine if increase is expected (traffic growth) or unexpected (misconfiguration, runaway job)
3. For unexpected: Mitigate within 4 hours, root cause within 24 hours
4. Document in cost anomaly tracker (Confluence: Engineering/Cost-Anomalies)

# High CPU Utilization Runbook

## Overview
This runbook covers investigation and remediation of high CPU utilization alerts on production servers.

---

## Threshold Definitions

| Level | Threshold | Duration | Action |
|-------|-----------|----------|--------|
| Warning | >80% | 5 minutes sustained | Investigate, no page |
| Critical | >95% | Immediate | Page on-call |
| P2 Incident | >95% | 15 minutes sustained | Declare P2 incident |
| Emergency | 100% | Any | Immediate P1, consider isolation |

---

## Step 1: Initial Assessment

When alerted for high CPU, first confirm the alert is real:

```bash
# Check current CPU usage
top -bn1 | head -20

# Check load average (1m, 5m, 15m)
uptime
# Load avg > 2x CPU count is concerning

# Check per-core utilization
mpstat -P ALL 1 3

# Check overall system stats
vmstat 1 10
```

**Interpreting results:**
- `us` (user CPU) high: Application is working hard — look for runaway processes
- `sy` (system CPU) high: Kernel overhead — check for high I/O or network interrupts
- `wa` (I/O wait) high: Disk I/O bottleneck — different problem (disk runbook applies)
- Load average consistently > 2x CPU core count: Queue building up, system under stress

---

## Step 2: Identify the Culprit

```bash
# Find top CPU consumers
ps aux --sort=-%cpu | head -20

# Detailed process tree
ps axjf | grep -A 5 <high-cpu-process>

# Check if it's a specific thread
top -H -p <PID>

# For Java processes: check GC
jstat -gcutil <PID> 1000 10
```

**Common root causes:**

### 2a. Runaway Process
- Single process at 100% CPU for >5 minutes
- Usually a bug (infinite loop, recursive call)
- Action: Capture stack trace, then kill or throttle

### 2b. Garbage Collection Pressure (Java/JVM)
- Multiple java processes at high CPU
- GC logs show frequent full GCs
- `jstat -gcutil` shows `FGC` counter rapidly increasing
- Action: Heap dump for analysis, consider restart if GC is >30% of CPU

### 2c. Memory Leak → Swap → CPU
- Low free memory: `free -h`
- High swap usage: `swapon -s`
- System spending CPU cycles swapping pages
- Action: Find memory-leaking process, restart it, scale up if recurring

### 2d. External DDoS or Traffic Spike
- High network interrupt CPU (`si` in vmstat)
- Many new connections in `netstat -an | grep ESTABLISHED | wc -l`
- Action: Rate limit, add WAF rules, scale horizontally

---

## Step 3: Remediation Flowchart

```
High CPU confirmed
    │
    ├─ Single runaway process?
    │      ├─ YES → capture stack trace → kill -9 <PID> → monitor
    │      └─ NO ↓
    ├─ GC pressure?
    │      ├─ YES → take heap dump → graceful restart → analyze heap
    │      └─ NO ↓
    ├─ Memory leak causing swap?
    │      ├─ YES → identify leaker → restart → file bug → scale up instance
    │      └─ NO ↓
    ├─ Traffic spike/DDoS?
    │      ├─ YES → enable rate limiting → add WAF rule → scale out
    │      └─ NO ↓
    └─ Unknown → escalate to L2, capture metrics, consider rolling restart
```

---

## Step 4: Post-Remediation Verification

1. Confirm CPU returns below 80%: `watch -n 5 'uptime'`
2. Confirm application health: `curl -sf http://localhost:<port>/health`
3. Check error rate in Grafana drops to baseline
4. Monitor for 15 minutes before closing the alert

---

## Escalation Criteria

Escalate to L2 if:
- CPU stays >90% for >10 minutes after intervention
- Multiple hosts affected simultaneously (fleet-wide issue)
- The high CPU is causing customer-visible errors
- Root cause is unknown after 20 minutes of investigation

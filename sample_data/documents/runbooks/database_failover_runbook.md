# Database Failover Runbook

## Overview
This runbook covers the procedure for failing over a PostgreSQL primary database to a standby replica. The procedure must be followed exactly. Deviating from steps can result in data loss or split-brain scenarios.

**RTO Target**: 5 minutes  
**RPO Target**: 30 seconds (based on streaming replication lag threshold)

---

## Failover Decision Criteria

Initiate failover when ALL of the following are true:
1. Primary database is unreachable from all application servers
2. OR replication lag has exceeded **30 seconds** for >5 minutes and primary health is degraded
3. At least one standby replica is confirmed healthy and in sync
4. Engineering Manager or on-call Lead has been notified

**Do NOT failover if:**
- Primary is reachable but slow (investigate root cause first)
- Replication lag is <30 seconds (transient lag, wait and monitor)
- No healthy standby exists (escalate to DBA team immediately)

---

## Pre-Failover Checklist

Run these checks before initiating failover:

```sql
-- On PRIMARY: Check replication status
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS replication_lag
FROM pg_stat_replication;

-- On STANDBY: Check lag in bytes
SELECT pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) AS lag_bytes;

-- Check if standby is still receiving WAL
SELECT now() - pg_last_xact_replay_timestamp() AS replication_delay;
```

**If replication delay > 30 seconds and primary is healthy**: Do NOT failover. Investigate replication issues.

---

## Failover Steps

### Step 1: Notify Stakeholders
Post in `#incidents`: "Database failover initiated. Primary: [hostname]. Standby: [hostname]. ETA: 5 minutes."

### Step 2: Stop Writes to Primary (if accessible)
```bash
# On primary: Put in read-only mode to prevent split-brain
psql -c "ALTER SYSTEM SET default_transaction_read_only = on;"
psql -c "SELECT pg_reload_conf();"
```

### Step 3: Promote Standby
```bash
# Option A: pg_ctl promote (PostgreSQL 12+)
pg_ctl promote -D /var/lib/postgresql/data

# Option B: Create trigger file (older versions)
touch /var/lib/postgresql/data/failover.trigger

# Verify promotion
psql -c "SELECT pg_is_in_recovery();"
# Should return: f (false = now primary)
```

### Step 4: Update Application Configuration
```bash
# Update connection string in application config
# From: postgresql://primary-db:5432/nexus
# To:   postgresql://standby-db:5432/nexus

# Kubernetes: Update secret
kubectl patch secret db-credentials -p '{"stringData":{"host":"standby-db"}}'

# Rolling restart to pick up new config
kubectl rollout restart deployment/api-deployment
kubectl rollout restart deployment/worker-deployment
```

### Step 5: Update DNS (if using DNS-based routing)
```bash
# Update CNAME: db.internal → standby-db.internal
# TTL should be 30s; wait for TTL to expire before proceeding
```

---

## Data Consistency Verification

After failover, verify data integrity:

```sql
-- Check LSN alignment (run on new primary)
SELECT pg_current_wal_lsn();

-- Count rows in critical tables (compare with backup snapshot)
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM tasks WHERE created_at > NOW() - INTERVAL '1 hour';

-- Check for any in-flight transactions that may have been lost
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

**Acceptable data loss**: Transactions committed after the last LSN received by standby may be lost. Document this window and notify product team if significant.

---

## Rollback Procedure (Failover Fails)

If the promoted standby shows corruption or data issues:

1. Stop all application traffic immediately
2. Put standby back in recovery mode (requires re-sync from a backup)
3. Contact DBA team on-call immediately
4. Declare P1 data incident
5. Restore from last verified backup — RTO resets to backup restoration time

---

## Post-Failover Actions

1. **Monitor** new primary for 30 minutes: replication, query performance, error rates
2. **Rebuild old primary** as new standby:
   - Restore from backup or use `pg_basebackup` from new primary
   - Configure `recovery.conf` to replicate from new primary
3. **Update monitoring** to alert on new primary hostname
4. **Schedule PIR** within 24 hours
5. **Document** RPO achieved (actual data loss window in seconds)

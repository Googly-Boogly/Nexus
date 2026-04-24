# Decommission Procedures

## Overview
This document defines the required process for safely decommissioning cloud resources to ensure no data loss, no billing continuity, and proper cleanup of all dependencies.

---

## Pre-Decommission Checklist

**Must be completed before any resource is terminated:**

### Traffic verification
- [ ] Confirm resource shows no active traffic in load balancer logs (last 24 hours)
- [ ] Confirm resource is removed from all load balancer target groups
- [ ] Confirm DNS records pointing to resource have been updated or removed
- [ ] Confirm application health dashboards show no dependency on this resource

### Dependency verification
- [ ] Check CMDB for any dependent systems
- [ ] Search codebase for hardcoded references to hostname/IP/endpoint
- [ ] Confirm no other services connect directly to this resource
- [ ] Verify Terraform/CloudFormation state does not reference this resource

### Data retention check
- [ ] Confirm no legal hold on data associated with this resource (check with Legal)
- [ ] Confirm compliance retention requirements are met (see Data Classification Policy)
- [ ] If data must be retained: confirm archive/migration is complete

### Backup verification
- [ ] Take final snapshot/backup labeled: `pre-decommission-YYYYMMDD-<resource-id>`
- [ ] Verify snapshot is complete and accessible
- [ ] Confirm backup is stored in the correct retention location

---

## Decommission Steps

### Step 1: Snapshot and Archive
```bash
# EC2: Create final AMI
aws ec2 create-image \
  --instance-id <instance-id> \
  --name "pre-decommission-$(date +%Y%m%d)-<service-name>" \
  --no-reboot

# RDS: Create final snapshot
aws rds create-db-snapshot \
  --db-instance-identifier <db-id> \
  --db-snapshot-identifier "pre-decommission-$(date +%Y%m%d)-<db-name>"

# EBS: Create volume snapshot
aws ec2 create-snapshot \
  --volume-id <volume-id> \
  --description "pre-decommission-$(date +%Y%m%d)"
```

### Step 2: DNS Cleanup
```bash
# Remove A/CNAME records from Route 53
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{"Changes":[{"Action":"DELETE","ResourceRecordSet":{...}}]}'

# Wait for TTL to expire before proceeding (check current TTL first)
```

### Step 3: Certificate Revocation
- Revoke any TLS certificates associated with the decommissioned hostname
- Remove hostname from any wildcard certificate SANs if applicable
- Update certificate in ACM if needed

### Step 4: Security Group Cleanup
```bash
# Remove the resource from all security group rules
# Check for rules referencing the resource's security group
aws ec2 describe-security-groups \
  --filters Name=ip-permission.group-id,Values=<sg-id>
```

### Step 5: Terminate Resource
```bash
# EC2 termination (irreversible after snapshot)
aws ec2 terminate-instances --instance-ids <instance-id>

# RDS deletion (with final snapshot)
aws rds delete-db-instance \
  --db-instance-identifier <db-id> \
  --final-db-snapshot-identifier "final-$(date +%Y%m%d)-<db-name>"
```

---

## Post-Decommission Verification

**Within 24 hours:**
- [ ] Confirm billing stops: Check AWS Cost Explorer for the resource ID
- [ ] Update CMDB: Mark resource as decommissioned with date
- [ ] Update Terraform state: Remove resource from state file
- [ ] Close ITSM decommission ticket

**Cost validation:**
- AWS bills in hourly increments; charges should stop within 1 hour for EC2
- RDS: Charges stop when instance is deleted (final snapshot has separate storage cost)
- EBS volumes: Charges continue until volumes are explicitly deleted (separate from EC2 termination if `DeleteOnTermination=false`)
- Verify next billing period shows expected reduction

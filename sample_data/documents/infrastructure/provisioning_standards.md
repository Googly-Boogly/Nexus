# Infrastructure Provisioning Standards v3.1

## Purpose
These standards define the requirements for provisioning cloud infrastructure at NEXUS Corp. All new resources must comply with these standards before receiving production traffic.

---

## VM Sizing Matrix

| Size | vCPU | RAM | Storage | Use Cases |
|------|------|-----|---------|-----------|
| small | 2 | 4GB | 50GB | Dev/test, lightweight workers |
| medium | 4 | 16GB | 100GB | Standard web/app servers, moderate workloads |
| large | 8 | 32GB | 200GB | High-traffic apps, data processing, caches |
| xlarge | 16 | 64GB | 500GB | Databases, ML inference, batch processing |
| 2xlarge | 32 | 128GB | 1TB | Large databases, high-memory analytics |

**For 500 req/s peak load**: Use `large` (8 vCPU / 32GB). Always provision 20% headroom above expected peak.

---

## Mandatory Tags

Every provisioned resource **must** have these tags or provisioning is rejected:

| Tag | Description | Example |
|-----|-------------|---------|
| `env` | Environment | `prod`, `staging`, `dev` |
| `team` | Owning team | `payments`, `platform`, `security` |
| `cost-center` | Finance cost center code | `CC-4821` |
| `owner` | Email of responsible engineer | `alice@nexus.corp` |
| `created-by` | Service or person that created it | `terraform/alice` |
| `data-classification` | Data sensitivity | `public`, `internal`, `confidential` |

**Optional but recommended**:
- `service`: Application service name (e.g., `payment-api`)
- `project`: Project or initiative (e.g., `checkout-v2`)
- `schedule`: Auto-shutdown schedule for non-prod (e.g., `weekdays-only`)

---

## Naming Convention

Format: `{env}-{service}-{region}-{index}`

Examples:
- `prod-web-use1-01` — Production web server, us-east-1, instance 1
- `staging-api-use1-02` — Staging API server, us-east-1, instance 2
- `dev-worker-euw1-01` — Dev worker, eu-west-1, instance 1

**Region codes**:
- `use1` = us-east-1
- `usw2` = us-west-2
- `euw1` = eu-west-1
- `apse1` = ap-southeast-1

---

## Security Baseline Requirements

All production EC2 instances and containers must:

### Prohibited configurations (automatic rejection)
- ❌ Security groups with `0.0.0.0/0` on any non-80/443 port
- ❌ Public IP address without WAF in front
- ❌ SSH (port 22) open to `0.0.0.0/0` (use Systems Manager Session Manager instead)
- ❌ IMDSv1 (must use IMDSv2: `HttpTokens=required`)
- ❌ Root EBS volume unencrypted
- ❌ S3 buckets with public access unless explicitly approved by CISO
- ❌ RDS instances without encryption at rest

### Required configurations
- ✅ IMDSv2 enabled (`HttpTokens=required`)
- ✅ All EBS volumes encrypted with KMS
- ✅ VPC security groups follow least-privilege
- ✅ SSM agent installed for patching and remote access
- ✅ CloudWatch agent installed for log shipping
- ✅ All instances in private subnets unless explicitly approved

---

## Storage Standards

- All S3 buckets: Versioning enabled, server-side encryption (SSE-S3 or SSE-KMS)
- All S3 buckets: Public access block enabled (no exceptions without CISO written approval)
- All S3 buckets: Lifecycle policies required (transition to IA after 30 days, Glacier after 90 days)
- All RDS: Multi-AZ enabled for production, automated backups enabled (7-day retention minimum)
- All EBS: Snapshots automated (daily, 7-day retention)

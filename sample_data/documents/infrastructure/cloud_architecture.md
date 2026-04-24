# Cloud Architecture Standards

## Multi-Account Strategy

NEXUS Corp uses an AWS Organizations multi-account structure for security isolation and blast radius control.

| Account | Purpose | Data Classification |
|---------|---------|-------------------|
| production | Production workloads | Confidential |
| staging | Pre-production testing | Internal |
| development | Developer sandboxes | Internal |
| security | Security tooling (SIEM, WAF, GuardDuty) | Confidential |
| shared-services | Shared infrastructure (logging, DNS, monitoring) | Internal |
| management | AWS Organizations management, billing | Confidential |

---

## Landing Zone

All new accounts are provisioned through Landing Zone automation:
- Baseline security controls applied automatically
- CloudTrail enabled in all regions
- AWS Config enabled with required rules
- GuardDuty enabled and integrated with central security account
- Default VPC deleted in all regions
- AWS Security Hub enabled
- Budgets and cost alerts configured

---

## Approved Architectural Patterns

### Pattern 1: Three-Tier Web Application
```
Internet → WAF → ALB → ECS (App Layer) → RDS PostgreSQL
                                        → ElastiCache Redis
                                        → S3 (Object Storage)
```
- Use when: Standard web application with REST API
- Must use: HTTPS only, WAF with OWASP ruleset, private RDS subnets
- Auto-scaling: Application tier scales on CPU/request count

### Pattern 2: Microservices on ECS
```
ALB → Target Group (per service) → ECS Service → ECR Image
                                               → Service Discovery
```
- Use when: Multiple independent services with different scaling needs
- Must use: Task-level IAM roles, secrets from Secrets Manager, ECR image scanning
- Service mesh: Optional (App Mesh) for complex service-to-service auth

### Pattern 3: Event-Driven (Celery/SQS)
```
API → SQS/Redis → Celery Worker → RDS/S3
```
- Use when: Long-running tasks, background processing
- Must use: DLQ (Dead Letter Queue), message visibility timeout 2x max task duration
- This is the NEXUS task execution pattern

---

## Prohibited Patterns

The following are **prohibited in production** without explicit CISO written waiver:

| Prohibited | Reason | Alternative |
|-----------|--------|------------|
| Public S3 buckets | Data exposure risk | CloudFront with OAC |
| Unencrypted RDS | Data protection | RDS with KMS encryption |
| Root account usage | Privilege abuse | Named IAM users with MFA |
| Long-lived IAM keys | Credential theft | IAM roles + instance profiles |
| Security groups with 0.0.0.0/0 on SSH | Unauthorized access | SSM Session Manager |
| Lambda with wildcard IAM | Privilege escalation | Least-privilege Lambda roles |
| Hardcoded secrets in code | Secret exposure | Secrets Manager / Parameter Store |

---

## CICD Pipeline Architecture

All production deployments must go through the approved CI/CD pipeline:

1. **Source**: GitHub (main branch only for production deploys)
2. **Build**: GitHub Actions or CodeBuild
3. **Test**: Unit tests + integration tests must pass (no exceptions)
4. **Security scan**: Checkov (IaC), Trivy (containers), SAST
5. **Staging deploy**: Automatic on merge to main
6. **Production deploy**: Manual approval gate (Engineering Manager)
7. **Post-deploy**: Automated smoke tests, synthetic monitoring

Hotfix deployments follow emergency change process (see Change Management policy).

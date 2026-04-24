# Network Topology and Architecture

## VPC Design

NEXUS Corp uses a multi-AZ, multi-subnet VPC design for all production workloads.

### Primary VPC Configuration

**Primary VPC**: `10.0.0.0/16` (us-east-1)
**Secondary VPC**: `10.1.0.0/16` (us-west-2, disaster recovery)

### Subnet Layout (per AZ, 3 AZs)

| Subnet Type | AZ-a | AZ-b | AZ-c | Purpose |
|-------------|------|------|------|---------|
| Public | 10.0.0.0/24 | 10.0.1.0/24 | 10.0.2.0/24 | Load balancers, NAT gateways |
| Private-App | 10.0.10.0/24 | 10.0.11.0/24 | 10.0.12.0/24 | Application servers, ECS tasks |
| Private-Data | 10.0.20.0/24 | 10.0.21.0/24 | 10.0.22.0/24 | Databases, ElastiCache, Qdrant |
| Management | 10.0.30.0/24 | 10.0.31.0/24 | 10.0.32.0/24 | Bastion hosts, monitoring |

---

## Security Zones

### DMZ (Public-Facing)
- Contains: Application Load Balancers, WAF, API Gateway
- All traffic filtered by WAF before reaching application tier
- No application servers directly in DMZ
- Security group: Allow 443/80 inbound from 0.0.0.0/0

### App Tier (Private)
- Contains: EC2 instances, ECS tasks, Lambda functions
- No direct internet access (all outbound via NAT Gateway)
- Inbound: Only from Load Balancer security group
- Security group: Allow 8080/8443 from ALB-SG only

### Data Tier (Isolated)
- Contains: RDS PostgreSQL, ElastiCache Redis, Qdrant, Kafka
- No internet access whatsoever (internal: true in isolation)
- Inbound: Only from App Tier security group
- Security group: Allow 5432 (PostgreSQL), 6379 (Redis), 6333 (Qdrant) from App-SG only

### Management (Restricted)
- Contains: Bastion hosts, monitoring agents (Prometheus, Grafana)
- Access: VPN-authenticated only
- All privileged sessions must originate from this zone
- Session recording mandatory

---

## Connectivity

### Internal Connectivity
- **Transit Gateway**: Connects all VPCs and accounts across regions
- **VPC Peering**: Used for same-region, same-account low-latency paths
- **PrivateLink**: For AWS service access without internet traversal

### External Connectivity
- **Primary**: AWS Direct Connect 1Gbps (dedicated circuit to on-premises datacenter)
- **Backup**: Site-to-Site VPN over public internet (automatic failover, ~100Mbps)
- **Internet Gateway**: For ALBs and NAT Gateways only

### DNS
- Internal: Route 53 Private Hosted Zone `nexus.internal`
- External: Route 53 Public Hosted Zone `nexus.example.com`
- Resolver: Route 53 Resolver for cross-account DNS resolution

---

## Network Access Control Lists (NACLs)

NACLs serve as a second layer of defense (security groups are primary):

| Rule | Direction | Protocol | Port | Action |
|------|-----------|----------|------|--------|
| 100 | Inbound | TCP | 443 | Allow |
| 110 | Inbound | TCP | 80 | Allow (redirect only) |
| 120 | Inbound | TCP | 1024-65535 | Allow (return traffic) |
| 32766 | Inbound | All | All | Deny |
| 100 | Outbound | All | All | Allow |

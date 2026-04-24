# IT Operations Glossary

A comprehensive reference for terms used in NEXUS Corp IT operations, SRE practices, and compliance.

---

## Incident and Reliability Metrics

**RTO** (Recovery Time Objective): The maximum acceptable time to restore a system after an outage. NEXUS targets: Critical systems 5 minutes, standard systems 30 minutes.

**RPO** (Recovery Point Objective): The maximum acceptable amount of data loss measured in time. NEXUS targets: Database 30 seconds (streaming replication), file storage 5 minutes.

**MTTR** (Mean Time To Recovery): Average time from incident start to full service restoration. Target: P1 < 1 hour, P2 < 4 hours.

**MTTF** (Mean Time To Failure): Average operating time between failures. Higher is better.

**MTBF** (Mean Time Between Failures): Average time between recoverable failures. MTBF = MTTF + MTTR.

**SLA** (Service Level Agreement): Contractual commitment to customers defining uptime, response time, and support levels.

**SLO** (Service Level Objective): Internal target (typically more aggressive than SLA). Example: 99.95% availability SLO when SLA is 99.9%.

**SLI** (Service Level Indicator): Quantitative measure of service quality. Example: % of requests completed in <200ms.

**Error budget**: The amount of downtime/errors allowed before breaching SLO. 99.9% SLO = 43.8 minutes/month error budget.

---

## Incident Classification

**P1**: Complete service outage, major data loss risk, >1000 customers affected. Requires immediate all-hands response.

**P2**: Significant degradation, >100 customers affected, critical subsystem down.

**P3**: Minor degradation, <100 customers affected, workaround available.

**P4**: Cosmetic issue, no customer impact.

**Blameless postmortem**: Post-incident review process focused on system and process improvement, not individual fault-finding.

**Toil**: Repetitive manual operational work that could be automated. SRE goal: Keep toil <50% of team time.

**Runbook**: Step-by-step operational procedure for a specific scenario (e.g., database failover runbook).

**Playbook**: Higher-level guide covering strategy and decision-making for complex scenarios.

---

## Database and Storage Terms

**DR** (Disaster Recovery): Capability to restore systems after catastrophic failure.

**BCP** (Business Continuity Plan): Plan for continuing operations during a major disruption.

**LSN** (Log Sequence Number): PostgreSQL internal identifier for position in write-ahead log.

**WAL** (Write-Ahead Log): PostgreSQL's transaction log. Used for replication and point-in-time recovery.

**PITR** (Point-In-Time Recovery): Ability to restore database to any specific moment in time using WAL.

**CMDB** (Configuration Management Database): Inventory of all IT assets and their relationships.

---

## DevOps and Cloud Terms

**ITSM** (IT Service Management): Framework for delivering IT services (e.g., ServiceNow, JIRA Service Desk).

**IaC** (Infrastructure as Code): Managing infrastructure through machine-readable definition files (Terraform, CloudFormation).

**GitOps**: Using Git as the single source of truth for infrastructure and application configuration.

**Blue-green deployment**: Running two identical production environments; switch traffic from old (blue) to new (green) atomically.

**Canary deployment**: Gradually shifting traffic percentage to new version; monitoring before full rollout.

**Chaos engineering**: Intentionally introducing failures to test system resilience (Chaos Monkey, Gremlin).

**Observability**: Ability to understand system internal state from external outputs (metrics, logs, traces — the "three pillars").

**DORA metrics** (DevOps Research and Assessment): Deployment frequency, lead time for changes, change failure rate, time to restore service.

---

## Networking Terms

**AZ** (Availability Zone): Isolated datacenter within a region.

**VPC** (Virtual Private Cloud): Logically isolated section of cloud network.

**CIDR** (Classless Inter-Domain Routing): Method for allocating IP addresses. Example: 10.0.0.0/16.

**BGP** (Border Gateway Protocol): Routing protocol used between autonomous systems (internet backbone).

**IGW** (Internet Gateway): VPC component enabling internet access.

**NAT** (Network Address Translation): Maps private IPs to public IPs for outbound internet access.

**SG** (Security Group): Virtual firewall for EC2 instances (stateful, allow-rules only).

**NACLs** (Network Access Control Lists): Subnet-level firewall (stateless, allow + deny rules).

---

## Security Terms

**IAM** (Identity and Access Management): Framework controlling who can do what in your systems.

**PAM** (Privileged Access Management): Security for elevated-privilege accounts (jump servers, session recording).

**SIEM** (Security Information and Event Management): Platform aggregating and analyzing security events (Splunk, Microsoft Sentinel).

**IDS** (Intrusion Detection System): Monitors network/system for malicious activity and generates alerts.

**IPS** (Intrusion Prevention System): Like IDS but also blocks detected threats.

**EDR** (Endpoint Detection and Response): Advanced endpoint security with behavioral analysis and response capabilities.

**SOC** (Security Operations Center): Team and facility responsible for security monitoring and incident response.

**NOC** (Network Operations Center): Team responsible for network monitoring and availability.

**SRE** (Site Reliability Engineering): Engineering discipline applying software principles to operations.

**CISO** (Chief Information Security Officer): Executive responsible for information security program.

**RCA** (Root Cause Analysis): Systematic process for identifying the fundamental cause of a problem.

**PIR** (Post-Incident Review): Structured review of an incident to identify improvements. Synonyms: postmortem, after-action review.

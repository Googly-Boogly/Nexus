# Network Outage Runbook

## Overview
Procedures for diagnosing and resolving network connectivity issues, from partial degradation to complete outages.

---

## Triage: Determine Scope

First, classify the outage type:

| Type | Symptoms | Likely Cause |
|------|----------|-------------|
| Internal LAN | VMs can't reach each other, external OK | Switch, VLAN, Security Group |
| WAN/Internet | Internal fine, no external connectivity | BGP, ISP, NAT Gateway |
| Partial | Some services affected, others fine | Specific route, firewall rule |
| DNS | Connectivity OK but resolution fails | DNS server, resolver config |
| Full | Complete outage affecting everything | Core router, carrier, power |

---

## Step 1: Confirm Scope

```bash
# Test internal connectivity
ping -c 3 10.0.1.1  # Internal gateway
ping -c 3 10.0.0.1  # VPC router

# Test external connectivity
ping -c 3 8.8.8.8    # Google DNS (bypasses DNS)
ping -c 3 1.1.1.1    # Cloudflare DNS

# Test DNS resolution
nslookup google.com
nslookup google.com 8.8.8.8  # Test against specific resolver
dig +short A api.external-service.com
```

---

## Step 2: DNS Resolution Checks

```bash
# Check /etc/resolv.conf
cat /etc/resolv.conf

# Test against primary nameserver
nslookup nexus-internal.corp <primary-dns-ip>

# Test against secondary nameserver
nslookup nexus-internal.corp <secondary-dns-ip>

# Check if systemd-resolved is running
systemctl status systemd-resolved

# Flush DNS cache
systemd-resolve --flush-caches
```

**If DNS is failing but IPs work**: Update `/etc/resolv.conf` to use secondary DNS or Google DNS (8.8.8.8) temporarily.

---

## Step 3: BGP and Routing Verification

```bash
# Check routing table
ip route show
ip route get <destination-ip>

# Check BGP peer status (requires router access)
# Cisco IOS equivalent: show ip bgp summary
# Bird: birdc show protocols

# Check NAT Gateway (AWS)
aws ec2 describe-nat-gateways --filter "Name=state,Values=available"

# Check VPN tunnel status
aws ec2 describe-vpn-connections --filter "Name=state,Values=available"
```

**BGP session down**: Contact ISP immediately. Verify BGP credentials and peer IP have not changed. Check for route advertisements.

---

## Step 4: Firewall and Security Group Audit

```bash
# List recent firewall rule changes (last 2 hours)
# AWS: Check CloudTrail for AuthorizeSecurityGroupIngress/Revoke events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --start-time $(date -d "2 hours ago" +%s)

# Check iptables rules (on Linux host)
iptables -L -n --line-numbers
iptables -L FORWARD -n

# Check for DENY rules that shouldn't be there
iptables -L -n | grep DROP
```

---

## Step 5: ISP Escalation

If BGP is down or WAN connectivity is lost:

1. Check ISP status page: [ISP-STATUS-URL]
2. Open support ticket with ISP:
   - **Priority**: P1 (complete outage) or P2 (degraded)
   - **Information to provide**: Circuit ID, affected IP ranges, last known-good time, symptoms observed
3. Escalate to NOC: `noc@isp.com` or NOC hotline
4. If ISP cannot restore within 30 minutes, activate **backup connectivity**:
   - Primary: Direct Connect (1Gbps)
   - Backup: Site-to-Site VPN over 4G LTE (limited bandwidth)

---

## Customer Communication

For outages >5 minutes affecting external users:

```
SERVICE ADVISORY — Network Impact
Time detected: [HH:MM UTC]
Status: We are experiencing network connectivity issues affecting [SCOPE].
Impact: [Description of what customers cannot do]
Our team is actively investigating. Next update in 15 minutes.
```

Update every 15 minutes until resolved.

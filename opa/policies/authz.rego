package nexus.authz
import future.keywords.in
import future.keywords.if

default allow = false

role_permissions := {
    "admin":    {"execute:incident_response","execute:infrastructure_provisioning","execute:compliance_scan",
                 "audit:view_all","audit:view_own","admin:manage_users","admin:system_metrics",
                 "approvals:review","knowledge:upload","knowledge:delete","knowledge:search",
                 "knowledge:admin"},
    "operator": {"execute:incident_response","execute:infrastructure_provisioning","execute:compliance_scan",
                 "audit:view_own","admin:system_metrics","knowledge:search"},
    "viewer":   {"audit:view_own","knowledge:search"}
}

clearance_level := {"public":0,"internal":1,"confidential":2}

allow if {
    input.action in role_permissions[input.user.role]
    clearance_level[input.user.clearance] >= clearance_level[input.resource.classification]
}

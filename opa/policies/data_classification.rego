package nexus.data
import future.keywords.if

agent_classification := {
    "incident_response":           "internal",
    "infrastructure_provisioning": "internal",
    "compliance_scan":             "confidential"
}

access_allowed if {
    required := agent_classification[input.agent_type]
    clearance_level[input.user.clearance] >= clearance_level[required]
}

clearance_level := {"public":0,"internal":1,"confidential":2}

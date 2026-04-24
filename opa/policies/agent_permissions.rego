package nexus.agents
import future.keywords.in
import future.keywords.if

allowed_tools := {
    "incident_response": {
        "check_system_status","query_application_logs","restart_service",
        "isolate_host","escalate_ticket","notify_on_call","query_knowledge_base"
    },
    "infrastructure_provisioning": {
        "create_virtual_machine","deploy_container","resize_resource",
        "check_quota","tag_resource","decommission_resource","query_knowledge_base"
    },
    "compliance_scan": {
        "scan_vulnerabilities","check_patch_status","audit_access_rights",
        "list_open_ports","check_encryption_status","generate_compliance_report",
        "query_knowledge_base"
    }
}

tool_allowed if { input.tool_name in allowed_tools[input.agent_type] }

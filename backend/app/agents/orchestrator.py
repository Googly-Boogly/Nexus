from app.agents.base_agent import BaseAgent
from app.agents.incident_agent import IncidentAgent
from app.agents.provisioning_agent import ProvisioningAgent
from app.agents.compliance_agent import ComplianceAgent


AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "incident_response": IncidentAgent,
    "infrastructure_provisioning": ProvisioningAgent,
    "compliance_scan": ComplianceAgent,
}


def get_agent(agent_type: str) -> BaseAgent:
    cls = AGENT_REGISTRY.get(agent_type)
    if cls is None:
        raise ValueError(f"Unknown agent type: {agent_type!r}. Available: {list(AGENT_REGISTRY)}")
    return cls()

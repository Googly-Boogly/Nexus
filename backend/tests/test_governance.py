import pytest


class TestGovernanceLayer:

    def setup_method(self):
        from app.core.governance import GovernanceLayer
        self.gov = GovernanceLayer()

    @pytest.mark.parametrize("text,pii_type", [
        ("SSN: 123-45-6789", "SSN"),
        ("Card: 4532015112830366", "credit_card"),
        ("Key: AKIAIOSFODNN7EXAMPLE", "aws_access_key"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private_key"),
        ("password=supersecret123", "password_literal"),
    ])
    def test_pii_detected(self, text, pii_type):
        result = self.gov.redact_pii(text)
        assert result.redacted
        assert pii_type in result.types_found

    def test_pii_redacted_in_output(self):
        result = self.gov.redact_pii("My SSN is 123-45-6789")
        assert "123-45-6789" not in result.text
        assert "REDACTED" in result.text

    def test_clean_text_not_redacted(self):
        result = self.gov.redact_pii("CPU utilization is at 87% on web-01")
        assert not result.redacted

    @pytest.mark.parametrize("cmd", [
        "rm -rf /var/data",
        "DROP TABLE users",
        "eval(user_input)",
        "exec(code)",
    ])
    def test_forbidden_commands_detected(self, cmd):
        found = self.gov.check_forbidden(cmd)
        assert len(found) > 0

    def test_allowed_command_passes(self):
        found = self.gov.check_forbidden("restart the payment service")
        assert found == []

    def test_length_check_pass(self):
        assert self.gov.check_length("short text")

    def test_length_check_fail(self):
        assert not self.gov.check_length("x" * 2001)

    def test_clearance_public_can_access_public(self):
        assert self.gov.check_clearance("public", "public")

    def test_clearance_internal_can_access_public(self):
        assert self.gov.check_clearance("internal", "public")

    def test_clearance_internal_can_access_internal(self):
        assert self.gov.check_clearance("internal", "internal")

    def test_clearance_internal_cannot_access_confidential(self):
        assert not self.gov.check_clearance("internal", "confidential")

    def test_clearance_confidential_can_access_all(self):
        assert self.gov.check_clearance("confidential", "confidential")


class TestSandbox:

    def setup_method(self):
        from app.core.sandbox import SandboxLayer
        self.sandbox = SandboxLayer()

    def test_allowed_tool_passes(self):
        self.sandbox.check_tool("incident_response", "check_system_status")

    def test_unauthorized_tool_raises(self):
        from app.core.sandbox import SandboxViolationError
        with pytest.raises(SandboxViolationError):
            self.sandbox.check_tool("incident_response", "create_virtual_machine")

    def test_filter_tools_drops_unauthorized(self):
        tools = [
            {"name": "check_system_status"},
            {"name": "create_virtual_machine"},
            {"name": "restart_service"},
        ]
        filtered, dropped = self.sandbox.filter_tools("incident_response", tools)
        assert len(dropped) == 1
        assert "create_virtual_machine" in dropped
        assert len(filtered) == 2

    def test_query_knowledge_base_allowed_all_agents(self):
        for agent_type in ("incident_response", "infrastructure_provisioning", "compliance_scan"):
            self.sandbox.check_tool(agent_type, "query_knowledge_base")

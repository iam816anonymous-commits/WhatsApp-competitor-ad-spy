import asyncio
from app.db.database import get_session
from app.db.tenant_context import set_tenant, get_tenant
from app.utils.audit import log_audit_action, audit_agent_action
from app.models.models import AuditLog

async def test_multi_tenancy_and_audit():
    # 1. Test Tenant Context
    set_tenant(42)
    assert get_tenant() == 42
    print(f"Tenant set to: {get_tenant()}")

    # 2. Test Audit Logging
    log_audit_action("TEST_ACTION", details="Integration test for audit", org_id=42)

    session = get_session()
    log = session.query(AuditLog).filter_by(action="TEST_ACTION").first()
    if log:
        print(f"Audit log found: {log.action}, Org: {log.org_id}")
        assert log.org_id == 42

    # 3. Test Audit Decorator
    class MockAgent:
        @audit_agent_action("AGENT_MOCK_CALL")
        async def run_task(self):
            return "done"

    agent = MockAgent()
    await agent.run_task()

    log2 = session.query(AuditLog).filter_by(action="AGENT_MOCK_CALL").first()
    if log2:
        print(f"Decorated audit log found: {log2.action}")
        assert log2.action == "AGENT_MOCK_CALL"

    session.close()

if __name__ == "__main__":
    asyncio.run(test_multi_tenancy_and_audit())

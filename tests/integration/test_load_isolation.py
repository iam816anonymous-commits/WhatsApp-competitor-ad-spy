import asyncio
from app.db.tenant_context import set_tenant, get_tenant
from app.orchestrator.engine import IntelligenceOrchestrator

async def test_concurrent_tenant_isolation():
    async def run_for_tenant(tid):
        set_tenant(tid)
        await asyncio.sleep(0.1) # Yield
        return get_tenant()

    results = await asyncio.gather(run_for_tenant(1), run_for_tenant(2), run_for_tenant(3))
    print(f"Isolated Tenants: {results}")
    assert results == [1, 2, 3]

if __name__ == "__main__":
    asyncio.run(test_concurrent_tenant_isolation())

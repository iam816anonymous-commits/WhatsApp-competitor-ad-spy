from contextvars import ContextVar
from typing import Optional

# Context variable to hold the current organization ID for multi-tenant isolation
current_org_id: ContextVar[Optional[int]] = ContextVar("current_org_id", default=None)

def set_tenant(org_id: int):
    current_org_id.set(org_id)

def get_tenant() -> Optional[int]:
    return current_org_id.get()

import logging
import functools
from typing import Optional
from app.db.database import get_session
from app.models.models import AuditLog

logger = logging.getLogger("AdSpyAgent.Audit")

def log_audit_action(action: str, details: Optional[str] = None, org_id: Optional[int] = None, user_id: Optional[int] = None):
    """
    Utility to log actions to the AuditLog table.
    """
    session = get_session()
    try:
        log_entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            details=details
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit action: {e}")
    finally:
        session.close()

def audit_agent_action(action_name: str):
    """
    Decorator to automatically audit agent methods.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try to extract org_id/user_id from args or kwargs if present
            # This is a simplified version
            res = await func(*args, **kwargs)
            log_audit_action(action_name, details=f"Method: {func.__name__} executed.")
            return res

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            log_audit_action(action_name, details=f"Method: {func.__name__} executed.")
            return res

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

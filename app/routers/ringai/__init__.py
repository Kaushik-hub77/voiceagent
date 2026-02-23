"""
RingAI router module
"""

from app.routers.ringai.calls import router as calls_router
from app.routers.ringai.webhooks import router as webhooks_router
from app.routers.ringai.webhook_config import router as webhook_config_router

__all__ = ["calls_router", "webhooks_router", "webhook_config_router"]


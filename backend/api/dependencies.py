"""
Shared FastAPI dependencies for API routes.

Traces: ARCH-003
"""

from backend.database import get_db

__all__ = ["get_db"]

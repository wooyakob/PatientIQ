"""
Tools for managing message routing in the healthcare agent system.
"""

import agentc
from datetime import datetime


def _get_db():
    from backend.database import db
    return db


@agentc.catalog.tool
def save_message_route(
    route_id: str,
    original_message: str,
    routed_to: list[str],
    priority: str,
    analysis: str = ""
) -> dict:
    """
    Save a message routing record to the database.

    Args:
        route_id: Unique identifier for the route
        original_message: The original announcement or message
        routed_to: List of staff member names/IDs to route to
        priority: Priority level (low, medium, high, urgent)
        analysis: Optional analysis of the routing decision

    Returns:
        Dictionary with success status
    """
    route_data = {
        "original_message": original_message,
        "routed_to": routed_to,
        "priority": priority,
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis
    }

    db = _get_db()
    success = db.save_message_route(route_id, route_data)

    return {
        "success": success,
        "route_id": route_id,
        "message": "Message route saved successfully" if success else "Failed to save route"
    }

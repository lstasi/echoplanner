"""EchoPlanner - Family Planner AI Agent Assistant."""

__version__ = "0.1.0"
__author__ = "EchoPlanner Team"
__email__ = "contact@echoplanner.com"
__description__ = "Family Planner AI Agent Assistant"

from .models.family import FamilyMember
from .models.calendar_event import CalendarEvent

__all__ = ["FamilyMember", "CalendarEvent"]
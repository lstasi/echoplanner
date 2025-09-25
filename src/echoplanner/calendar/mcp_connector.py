"""MCP (Model Context Protocol) connector for calendar integration."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

import httpx
from icalendar import Calendar, Event as ICalEvent

from ..config.settings import Settings
from ..models.calendar_event import CalendarEvent, EventRecurrence, RecurrencePattern

logger = logging.getLogger(__name__)


class MCPConnector:
    """Connector for integrating with calendar systems via MCP protocol."""
    
    def __init__(self, settings: Settings):
        """Initialize MCP connector with settings."""
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = settings.mcp_server_url
        self.api_key = settings.mcp_api_key
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def create_event(self, event: CalendarEvent) -> bool:
        """Create a new calendar event via MCP."""
        if not self._is_configured():
            logger.warning("MCP connector not configured, skipping event creation")
            return False
        
        try:
            # Convert CalendarEvent to MCP format
            mcp_event_data = self._convert_to_mcp_format(event)
            
            # Make API call to create event
            response = await self._make_mcp_request(
                method="POST",
                endpoint="/events",
                data=mcp_event_data
            )
            
            if response and response.get("success"):
                logger.info(f"Successfully created calendar event: {event.title}")
                return True
            else:
                logger.error(f"Failed to create calendar event: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating calendar event via MCP: {e}")
            return False
    
    async def update_event(self, event: CalendarEvent) -> bool:
        """Update an existing calendar event via MCP."""
        if not self._is_configured():
            logger.warning("MCP connector not configured, skipping event update")
            return False
        
        try:
            # Convert CalendarEvent to MCP format
            mcp_event_data = self._convert_to_mcp_format(event)
            
            # Make API call to update event
            response = await self._make_mcp_request(
                method="PUT",
                endpoint=f"/events/{event.id}",
                data=mcp_event_data
            )
            
            if response and response.get("success"):
                logger.info(f"Successfully updated calendar event: {event.title}")
                return True
            else:
                logger.error(f"Failed to update calendar event: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating calendar event via MCP: {e}")
            return False
    
    async def delete_event(self, event_id: UUID) -> bool:
        """Delete a calendar event via MCP."""
        if not self._is_configured():
            logger.warning("MCP connector not configured, skipping event deletion")
            return False
        
        try:
            # Make API call to delete event
            response = await self._make_mcp_request(
                method="DELETE",
                endpoint=f"/events/{event_id}"
            )
            
            if response and response.get("success"):
                logger.info(f"Successfully deleted calendar event: {event_id}")
                return True
            else:
                logger.error(f"Failed to delete calendar event: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting calendar event via MCP: {e}")
            return False
    
    async def get_events(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        member_ids: Optional[List[UUID]] = None
    ) -> List[CalendarEvent]:
        """Retrieve calendar events via MCP."""
        if not self._is_configured():
            logger.warning("MCP connector not configured, returning empty list")
            return []
        
        try:
            # Build query parameters
            params = {}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            if member_ids:
                params["member_ids"] = [str(mid) for mid in member_ids]
            
            # Make API call to get events
            response = await self._make_mcp_request(
                method="GET",
                endpoint="/events",
                params=params
            )
            
            if response and response.get("success"):
                events_data = response.get("data", [])
                events = []
                
                for event_data in events_data:
                    try:
                        event = self._convert_from_mcp_format(event_data)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.error(f"Error converting MCP event data: {e}")
                        continue
                
                logger.info(f"Retrieved {len(events)} calendar events via MCP")
                return events
            else:
                logger.error(f"Failed to retrieve calendar events: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving calendar events via MCP: {e}")
            return []
    
    async def export_to_ical(self, events: List[CalendarEvent]) -> str:
        """Export events to iCal format."""
        try:
            cal = Calendar()
            cal.add('prodid', '-//EchoPlanner//Family Calendar//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            
            for event in events:
                ical_event = ICalEvent()
                ical_event.add('uid', str(event.id))
                ical_event.add('summary', event.title)
                ical_event.add('dtstart', event.start_datetime)
                
                if event.end_datetime:
                    ical_event.add('dtend', event.end_datetime)
                
                if event.description:
                    ical_event.add('description', event.description)
                
                if event.location:
                    ical_event.add('location', event.location)
                
                ical_event.add('created', event.created_at)
                ical_event.add('last-modified', event.updated_at)
                
                # Add recurrence rules if applicable
                if event.recurrence and event.recurrence.pattern != RecurrencePattern.NONE:
                    rrule = self._build_rrule(event.recurrence)
                    if rrule:
                        ical_event.add('rrule', rrule)
                
                cal.add_component(ical_event)
            
            return cal.to_ical().decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error exporting to iCal: {e}")
            return ""
    
    def _is_configured(self) -> bool:
        """Check if MCP connector is properly configured."""
        return bool(self.base_url and self.api_key)
    
    async def _make_mcp_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to MCP server."""
        if not self._is_configured():
            raise ValueError("MCP connector not configured")
        
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"MCP API request error: {e}")
            return None
    
    def _convert_to_mcp_format(self, event: CalendarEvent) -> Dict[str, Any]:
        """Convert CalendarEvent to MCP format."""
        mcp_data = {
            "id": str(event.id),
            "title": event.title,
            "description": event.description,
            "start_datetime": event.start_datetime.isoformat(),
            "all_day": event.all_day,
            "location": event.location,
            "event_type": event.event_type.value,
            "priority": event.priority.value,
            "assigned_members": [str(mid) for mid in event.assigned_members],
            "tags": event.tags,
            "notes": event.notes,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            "is_active": event.is_active
        }
        
        if event.end_datetime:
            mcp_data["end_datetime"] = event.end_datetime.isoformat()
        
        if event.recurrence:
            mcp_data["recurrence"] = {
                "pattern": event.recurrence.pattern.value,
                "interval": event.recurrence.interval,
                "days_of_week": event.recurrence.days_of_week,
                "day_of_month": event.recurrence.day_of_month,
                "end_date": event.recurrence.end_date.isoformat() if event.recurrence.end_date else None,
                "max_occurrences": event.recurrence.max_occurrences
            }
        
        return mcp_data
    
    def _convert_from_mcp_format(self, data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Convert MCP format data to CalendarEvent."""
        try:
            # Parse dates
            start_datetime = datetime.fromisoformat(data["start_datetime"])
            end_datetime = None
            if data.get("end_datetime"):
                end_datetime = datetime.fromisoformat(data["end_datetime"])
            
            created_at = datetime.fromisoformat(data["created_at"])
            updated_at = datetime.fromisoformat(data["updated_at"])
            
            # Create event
            event = CalendarEvent(
                id=UUID(data["id"]),
                title=data["title"],
                description=data.get("description"),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                all_day=data.get("all_day", False),
                location=data.get("location"),
                event_type=data.get("event_type", "other"),
                priority=data.get("priority", "medium"),
                assigned_members=[UUID(mid) for mid in data.get("assigned_members", [])],
                tags=data.get("tags", []),
                notes=data.get("notes"),
                created_at=created_at,
                updated_at=updated_at,
                is_active=data.get("is_active", True)
            )
            
            # Handle recurrence
            if data.get("recurrence"):
                rec_data = data["recurrence"]
                event.recurrence = EventRecurrence(
                    pattern=RecurrencePattern(rec_data["pattern"]),
                    interval=rec_data.get("interval", 1),
                    days_of_week=rec_data.get("days_of_week"),
                    day_of_month=rec_data.get("day_of_month"),
                    end_date=datetime.fromisoformat(rec_data["end_date"]) if rec_data.get("end_date") else None,
                    max_occurrences=rec_data.get("max_occurrences")
                )
            
            return event
            
        except Exception as e:
            logger.error(f"Error converting from MCP format: {e}")
            return None
    
    def _build_rrule(self, recurrence: EventRecurrence) -> Optional[Dict[str, Any]]:
        """Build iCal RRULE from EventRecurrence."""
        if recurrence.pattern == RecurrencePattern.NONE:
            return None
        
        rrule = {
            'FREQ': recurrence.pattern.value.upper(),
            'INTERVAL': recurrence.interval
        }
        
        if recurrence.days_of_week:
            # Convert to iCal day format (MO, TU, WE, etc.)
            days = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
            rrule['BYDAY'] = [days[day] for day in recurrence.days_of_week]
        
        if recurrence.day_of_month:
            rrule['BYMONTHDAY'] = recurrence.day_of_month
        
        if recurrence.end_date:
            rrule['UNTIL'] = recurrence.end_date
        
        if recurrence.max_occurrences:
            rrule['COUNT'] = recurrence.max_occurrences
        
        return rrule
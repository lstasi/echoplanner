"""Local calendar storage using JSON files."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..config.settings import Settings
from ..models.calendar_event import CalendarEvent
from ..models.family import Family, FamilyMember

logger = logging.getLogger(__name__)


class CalendarStorage:
    """Local storage for calendar events and family data using JSON files."""
    
    def __init__(self, settings: Settings):
        """Initialize calendar storage with settings."""
        self.settings = settings
        self.events_file = settings.data_dir / "events.json"
        self.family_file = settings.data_dir / "family.json"
        self.processed_emails_file = settings.data_dir / "processed_emails.json"
        
        # Ensure data directory exists
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    
    # Family Management
    async def save_family(self, family: Family) -> bool:
        """Save family data to storage."""
        try:
            family_data = family.dict()
            
            with open(self.family_file, 'w', encoding='utf-8') as f:
                json.dump(family_data, f, indent=2, default=self._json_serializer)
            
            logger.info(f"Saved family data: {family.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving family data: {e}")
            return False
    
    async def load_family(self) -> Optional[Family]:
        """Load family data from storage."""
        try:
            if not self.family_file.exists():
                logger.info("No family data file found, creating default family")
                return self._create_default_family()
            
            with open(self.family_file, 'r', encoding='utf-8') as f:
                family_data = json.load(f)
            
            # Convert string UUIDs back to UUID objects
            family_data = self._deserialize_uuids(family_data)
            
            family = Family(**family_data)
            logger.info(f"Loaded family data: {family.name}")
            return family
            
        except Exception as e:
            logger.error(f"Error loading family data: {e}")
            return self._create_default_family()
    
    def _create_default_family(self) -> Family:
        """Create a default family configuration."""
        return Family(
            name="Default Family",
            settings={
                "timezone": self.settings.calendar_timezone,
                "created_by": "echoplanner_system"
            }
        )
    
    # Event Management
    async def save_event(self, event: CalendarEvent) -> bool:
        """Save a single calendar event to storage."""
        try:
            events = await self.load_events()
            
            # Update existing event or add new one
            updated = False
            for i, existing_event in enumerate(events):
                if existing_event.id == event.id:
                    events[i] = event
                    updated = True
                    break
            
            if not updated:
                events.append(event)
            
            return await self.save_events(events)
            
        except Exception as e:
            logger.error(f"Error saving event: {e}")
            return False
    
    async def save_events(self, events: List[CalendarEvent]) -> bool:
        """Save all calendar events to storage."""
        try:
            events_data = [event.dict() for event in events]
            
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2, default=self._json_serializer)
            
            logger.info(f"Saved {len(events)} calendar events")
            return True
            
        except Exception as e:
            logger.error(f"Error saving events: {e}")
            return False
    
    async def load_events(self) -> List[CalendarEvent]:
        """Load all calendar events from storage."""
        try:
            if not self.events_file.exists():
                logger.info("No events file found, returning empty list")
                return []
            
            with open(self.events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            
            events = []
            for event_data in events_data:
                try:
                    # Convert string UUIDs back to UUID objects and dates
                    event_data = self._deserialize_event_data(event_data)
                    event = CalendarEvent(**event_data)
                    events.append(event)
                except Exception as e:
                    logger.error(f"Error deserializing event: {e}")
                    continue
            
            logger.info(f"Loaded {len(events)} calendar events")
            return events
            
        except Exception as e:
            logger.error(f"Error loading events: {e}")
            return []
    
    async def get_events_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events within a specific date range."""
        events = await self.load_events()
        
        filtered_events = []
        for event in events:
            if not event.is_active:
                continue
            
            # Check if event overlaps with date range
            event_start = event.start_datetime
            event_end = event.end_datetime or event_start
            
            if event_start <= end_date and event_end >= start_date:
                filtered_events.append(event)
        
        return filtered_events
    
    async def get_events_by_member(self, member_id: UUID) -> List[CalendarEvent]:
        """Get events assigned to a specific family member."""
        events = await self.load_events()
        
        member_events = []
        for event in events:
            if not event.is_active:
                continue
            
            if member_id in event.assigned_members:
                member_events.append(event)
        
        return member_events
    
    async def delete_event(self, event_id: UUID) -> bool:
        """Delete a calendar event."""
        try:
            events = await self.load_events()
            
            updated_events = [event for event in events if event.id != event_id]
            
            if len(updated_events) == len(events):
                logger.warning(f"Event {event_id} not found for deletion")
                return False
            
            success = await self.save_events(updated_events)
            if success:
                logger.info(f"Deleted event {event_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False
    
    # Email Processing Storage
    async def save_processed_email(self, email_data: Dict[str, Any]) -> bool:
        """Save processed email information."""
        try:
            processed_emails = await self.load_processed_emails()
            processed_emails.append(email_data)
            
            with open(self.processed_emails_file, 'w', encoding='utf-8') as f:
                json.dump(processed_emails, f, indent=2, default=self._json_serializer)
            
            logger.info(f"Saved processed email data")
            return True
            
        except Exception as e:
            logger.error(f"Error saving processed email: {e}")
            return False
    
    async def load_processed_emails(self) -> List[Dict[str, Any]]:
        """Load processed email information."""
        try:
            if not self.processed_emails_file.exists():
                return []
            
            with open(self.processed_emails_file, 'r', encoding='utf-8') as f:
                processed_emails = json.load(f)
            
            logger.info(f"Loaded {len(processed_emails)} processed emails")
            return processed_emails
            
        except Exception as e:
            logger.error(f"Error loading processed emails: {e}")
            return []
    
    # Cleanup Operations
    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old processed emails and inactive events."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Clean up old processed emails
            processed_emails = await self.load_processed_emails()
            active_emails = []
            
            for email_data in processed_emails:
                try:
                    created_at = datetime.fromisoformat(email_data.get("created_at", ""))
                    if created_at > cutoff_date:
                        active_emails.append(email_data)
                except Exception:
                    # Keep emails with invalid dates (better safe than sorry)
                    active_emails.append(email_data)
            
            if len(active_emails) < len(processed_emails):
                with open(self.processed_emails_file, 'w', encoding='utf-8') as f:
                    json.dump(active_emails, f, indent=2, default=self._json_serializer)
                logger.info(f"Cleaned up {len(processed_emails) - len(active_emails)} old processed emails")
            
            # Clean up old inactive events
            events = await self.load_events()
            active_events = []
            
            for event in events:
                # Keep active events and recent inactive events
                if event.is_active or event.updated_at > cutoff_date:
                    active_events.append(event)
            
            if len(active_events) < len(events):
                await self.save_events(active_events)
                logger.info(f"Cleaned up {len(events) - len(active_events)} old events")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Statistics and Reporting
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            events = await self.load_events()
            processed_emails = await self.load_processed_emails()
            family = await self.load_family()
            
            stats = {
                "total_events": len(events),
                "active_events": len([e for e in events if e.is_active]),
                "processed_emails": len(processed_emails),
                "family_members": len(family.members) if family else 0,
                "data_directory": str(self.settings.data_dir),
                "files": {
                    "events_file_exists": self.events_file.exists(),
                    "family_file_exists": self.family_file.exists(),
                    "emails_file_exists": self.processed_emails_file.exists()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}
    
    # Utility Methods
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and UUID objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _deserialize_uuids(self, data):
        """Convert string UUIDs back to UUID objects in nested dictionaries."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key.endswith('_id') or key == 'id':
                    try:
                        result[key] = UUID(value) if isinstance(value, str) else value
                    except (ValueError, TypeError):
                        result[key] = value
                elif key == 'assigned_members' and isinstance(value, list):
                    result[key] = [UUID(v) if isinstance(v, str) else v for v in value]
                elif isinstance(value, (dict, list)):
                    result[key] = self._deserialize_uuids(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._deserialize_uuids(item) for item in data]
        else:
            return data
    
    def _deserialize_event_data(self, data):
        """Deserialize event data with proper type conversion."""
        # Convert UUID fields
        data = self._deserialize_uuids(data)
        
        # Convert datetime fields
        datetime_fields = ['start_datetime', 'end_datetime', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in data and data[field]:
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid datetime format for field {field}: {data[field]}")
                    data[field] = datetime.utcnow()
        
        # Handle recurrence end_date
        if 'recurrence' in data and data['recurrence'] and 'end_date' in data['recurrence']:
            if data['recurrence']['end_date']:
                try:
                    data['recurrence']['end_date'] = datetime.fromisoformat(data['recurrence']['end_date'])
                except (ValueError, TypeError):
                    data['recurrence']['end_date'] = None
        
        return data
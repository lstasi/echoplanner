"""Calendar event data models."""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class EventType(str, Enum):
    """Types of calendar events."""
    APPOINTMENT = "appointment"
    MEETING = "meeting"
    REMINDER = "reminder"
    BIRTHDAY = "birthday"
    HOLIDAY = "holiday"
    TASK = "task"
    MEAL = "meal"
    ACTIVITY = "activity"
    OTHER = "other"


class EventPriority(str, Enum):
    """Event priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecurrencePattern(str, Enum):
    """Recurrence pattern types."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EventRecurrence(BaseModel):
    """Event recurrence configuration."""
    
    pattern: RecurrencePattern = Field(default=RecurrencePattern.NONE, description="Recurrence pattern")
    interval: int = Field(default=1, ge=1, description="Interval between occurrences")
    days_of_week: Optional[List[int]] = Field(None, description="Days of week for weekly recurrence (0=Monday)")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="Day of month for monthly recurrence")
    end_date: Optional[datetime] = Field(None, description="End date for recurrence")
    max_occurrences: Optional[int] = Field(None, ge=1, description="Maximum number of occurrences")
    
    @validator('days_of_week')
    def validate_days_of_week(cls, v):
        """Validate days of week are in valid range."""
        if v is not None:
            for day in v:
                if not 0 <= day <= 6:
                    raise ValueError('Days of week must be between 0 (Monday) and 6 (Sunday)')
        return v


class CalendarEvent(BaseModel):
    """Represents a calendar event in the family planner."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the event")
    title: str = Field(..., min_length=1, max_length=200, description="Event title")
    description: Optional[str] = Field(None, max_length=1000, description="Event description")
    start_datetime: datetime = Field(..., description="Event start date and time")
    end_datetime: Optional[datetime] = Field(None, description="Event end date and time")
    all_day: bool = Field(default=False, description="Whether this is an all-day event")
    location: Optional[str] = Field(None, max_length=200, description="Event location")
    event_type: EventType = Field(default=EventType.OTHER, description="Type of event")
    priority: EventPriority = Field(default=EventPriority.MEDIUM, description="Event priority")
    
    # Family member associations
    assigned_members: List[UUID] = Field(default_factory=list, description="Family member IDs assigned to this event")
    created_by: Optional[UUID] = Field(None, description="Family member who created this event")
    
    # Recurrence
    recurrence: Optional[EventRecurrence] = Field(None, description="Recurrence configuration")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Event tags for categorization")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes")
    attachments: List[str] = Field(default_factory=list, description="File attachment paths")
    
    # System fields
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the event was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether the event is active")
    
    # AI processing metadata
    source_email_id: Optional[str] = Field(None, description="Source email ID if created from email")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI processing confidence score")
    ai_extracted_data: dict = Field(default_factory=dict, description="Raw AI extracted data")
    
    @validator('end_datetime')
    def validate_end_after_start(cls, v, values):
        """Validate end datetime is after start datetime."""
        if v is not None and 'start_datetime' in values:
            if v <= values['start_datetime']:
                raise ValueError('End datetime must be after start datetime')
        return v
    
    @validator('title')
    def validate_title(cls, v):
        """Validate title is not empty or whitespace only."""
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate and normalize tags."""
        return [tag.strip().lower() for tag in v if tag.strip()]
    
    def add_member(self, member_id: UUID) -> None:
        """Add a family member to this event."""
        if member_id not in self.assigned_members:
            self.assigned_members.append(member_id)
            self.updated_at = datetime.utcnow()
    
    def remove_member(self, member_id: UUID) -> bool:
        """Remove a family member from this event."""
        if member_id in self.assigned_members:
            self.assigned_members.remove(member_id)
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the event."""
        normalized_tag = tag.strip().lower()
        if normalized_tag and normalized_tag not in self.tags:
            self.tags.append(normalized_tag)
            self.updated_at = datetime.utcnow()
    
    def get_duration(self) -> Optional[timedelta]:
        """Get event duration if end datetime is set."""
        if self.end_datetime:
            return self.end_datetime - self.start_datetime
        return None
    
    def is_recurring(self) -> bool:
        """Check if event has recurrence configured."""
        return self.recurrence is not None and self.recurrence.pattern != RecurrencePattern.NONE
    
    def is_multi_day(self) -> bool:
        """Check if event spans multiple days."""
        if self.end_datetime:
            return self.end_datetime.date() > self.start_datetime.date()
        return False
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
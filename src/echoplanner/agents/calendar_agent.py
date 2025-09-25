"""Calendar agent for extracting calendar events from text using AI."""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

import openai
from dateutil import parser as date_parser

from ..config.settings import Settings
from ..models.calendar_event import CalendarEvent, EventPriority, EventType, RecurrencePattern
from ..models.family import Family, FamilyMember

logger = logging.getLogger(__name__)


class CalendarAgent:
    """AI agent for extracting calendar events from text content."""
    
    def __init__(self, settings: Settings, family: Family):
        """Initialize calendar agent with settings and family context."""
        self.settings = settings
        self.family = family
        
        # Initialize OpenAI client if API key is provided
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
        else:
            logger.warning("OpenAI API key not provided, calendar extraction will be limited")
    
    async def extract_events_from_text(
        self, 
        text: str, 
        sender: str, 
        subject: str,
        received_at: datetime
    ) -> List[CalendarEvent]:
        """Extract calendar events from text using AI."""
        if not self.settings.openai_api_key:
            logger.warning("OpenAI API key not configured, using fallback extraction")
            return self._fallback_extraction(text, sender, subject, received_at)
        
        try:
            # Prepare context about family members
            family_context = self._build_family_context()
            
            # Create AI prompt
            prompt = self._build_extraction_prompt(text, sender, subject, family_context)
            
            # Call OpenAI API
            response = await self._call_openai_api(prompt)
            
            # Parse AI response
            events = self._parse_ai_response(response, sender, received_at)
            
            logger.info(f"AI extracted {len(events)} events from text")
            return events
            
        except Exception as e:
            logger.error(f"Error in AI extraction: {e}")
            # Fall back to rule-based extraction
            return self._fallback_extraction(text, sender, subject, received_at)
    
    def _build_family_context(self) -> str:
        """Build context string about family members."""
        context_parts = []
        context_parts.append("Family Members:")
        
        for member in self.family.members:
            member_info = f"- {member.name}"
            if member.role:
                member_info += f" (Role: {member.role.value})"
            if member.age:
                member_info += f" (Age: {member.age})"
            context_parts.append(member_info)
        
        return "\n".join(context_parts)
    
    def _build_extraction_prompt(self, text: str, sender: str, subject: str, family_context: str) -> str:
        """Build the AI prompt for calendar event extraction."""
        return f"""
You are a family calendar assistant. Extract calendar events from the following email content.

{family_context}

Email Details:
- From: {sender}
- Subject: {subject}

Email Content:
{text}

Please extract calendar events and return them as a JSON array. For each event, include:
- title: Brief descriptive title
- description: More detailed description if available
- start_datetime: ISO format datetime (YYYY-MM-DDTHH:MM:SS)
- end_datetime: ISO format datetime if specified or can be inferred
- all_day: true/false
- location: if mentioned
- event_type: one of {[t.value for t in EventType]}
- priority: one of {[p.value for p in EventPriority]}
- assigned_members: array of family member names mentioned
- recurrence_pattern: one of {[r.value for r in RecurrencePattern]}
- tags: array of relevant tags
- ai_confidence: confidence score between 0.0 and 1.0

Guidelines:
- Infer reasonable defaults for missing information
- Use context clues to determine family members involved
- Recognize common recurring patterns like "every week", "monthly", etc.
- Set appropriate event types based on content
- Include confidence score based on how clear the information is
- Current date/time context: {datetime.now().isoformat()}

Return only the JSON array, no other text.
"""
    
    async def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API with the extraction prompt."""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful calendar extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.settings.ai_temperature,
                max_tokens=self.settings.ai_max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_ai_response(self, response: str, sender: str, received_at: datetime) -> List[CalendarEvent]:
        """Parse AI response JSON into CalendarEvent objects."""
        events = []
        
        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response
            
            events_data = json.loads(json_str)
            
            for event_data in events_data:
                try:
                    event = self._create_event_from_data(event_data, sender, received_at)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error creating event from data: {e}")
                    continue
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
        
        return events
    
    def _create_event_from_data(self, data: dict, sender: str, received_at: datetime) -> Optional[CalendarEvent]:
        """Create CalendarEvent from parsed data dictionary."""
        try:
            # Parse datetime strings
            start_datetime = self._parse_datetime(data.get("start_datetime"))
            if not start_datetime:
                logger.warning("No valid start datetime found, skipping event")
                return None
            
            end_datetime = None
            if data.get("end_datetime"):
                end_datetime = self._parse_datetime(data.get("end_datetime"))
            
            # Find assigned family members
            assigned_member_ids = self._resolve_family_members(data.get("assigned_members", []))
            
            # Create event
            event = CalendarEvent(
                title=data.get("title", "Untitled Event"),
                description=data.get("description"),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                all_day=data.get("all_day", False),
                location=data.get("location"),
                event_type=EventType(data.get("event_type", EventType.OTHER.value)),
                priority=EventPriority(data.get("priority", EventPriority.MEDIUM.value)),
                assigned_members=assigned_member_ids,
                tags=data.get("tags", []),
                ai_confidence=data.get("ai_confidence", 0.5),
                ai_extracted_data=data
            )
            
            # Handle recurrence if specified
            recurrence_pattern = data.get("recurrence_pattern")
            if recurrence_pattern and recurrence_pattern != RecurrencePattern.NONE.value:
                from ..models.calendar_event import EventRecurrence
                event.recurrence = EventRecurrence(
                    pattern=RecurrencePattern(recurrence_pattern)
                )
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating event from data: {e}")
            return None
    
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string into datetime object."""
        if not datetime_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try dateutil parser as fallback
                return date_parser.parse(datetime_str)
            except Exception as e:
                logger.error(f"Failed to parse datetime '{datetime_str}': {e}")
                return None
    
    def _resolve_family_members(self, member_names: List[str]) -> List[str]:
        """Resolve family member names to UUIDs."""
        resolved_ids = []
        
        for name in member_names:
            name_lower = name.lower().strip()
            for member in self.family.members:
                if member.name.lower() == name_lower:
                    resolved_ids.append(str(member.id))
                    break
        
        return resolved_ids
    
    def _fallback_extraction(
        self, 
        text: str, 
        sender: str, 
        subject: str, 
        received_at: datetime
    ) -> List[CalendarEvent]:
        """Fallback rule-based extraction when AI is not available."""
        events = []
        
        # Simple rule-based patterns
        patterns = [
            # Date and time patterns
            (r'(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)', 'appointment'),
            (r'on\s+(\w+)\s+(\d{1,2}(?:st|nd|rd|th)?)\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)', 'meeting'),
            (r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s+(?:on\s+)?(\d{1,2}/\d{1,2})', 'reminder'),
        ]
        
        for pattern, event_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Basic event creation from pattern match
                    event = CalendarEvent(
                        title=f"Event from {subject}",
                        description=text[:200] + "..." if len(text) > 200 else text,
                        start_datetime=received_at + timedelta(days=1),  # Default to tomorrow
                        event_type=EventType(event_type),
                        ai_confidence=0.3,  # Low confidence for rule-based
                        ai_extracted_data={"extraction_method": "rule_based", "pattern": pattern}
                    )
                    events.append(event)
                except Exception as e:
                    logger.error(f"Error creating fallback event: {e}")
                    continue
        
        logger.info(f"Fallback extraction found {len(events)} events")
        return events
"""Email processor that coordinates AI agents to extract calendar events."""

import logging
from datetime import datetime
from typing import List, Optional

from ..agents.calendar_agent import CalendarAgent
from ..agents.image_agent import ImageAgent
from ..agents.voice_agent import VoiceAgent
from ..config.settings import Settings
from ..models.calendar_event import CalendarEvent
from ..models.email_input import AttachmentType, EmailInput
from ..models.family import Family

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Processes emails using multiple AI agents to extract calendar events."""
    
    def __init__(self, settings: Settings, family: Family):
        """Initialize email processor with settings and family context."""
        self.settings = settings
        self.family = family
        self.calendar_agent = CalendarAgent(settings, family)
        self.image_agent = ImageAgent(settings)
        self.voice_agent = VoiceAgent(settings)
    
    async def process_email(self, email_input: EmailInput) -> List[CalendarEvent]:
        """Process an email and extract calendar events."""
        logger.info(f"Processing email: {email_input.subject}")
        
        email_input.mark_processing_started()
        
        try:
            # Check if sender is from allowed domain
            if not self.settings.is_email_domain_allowed(email_input.sender):
                logger.warning(f"Email from {email_input.sender} not from allowed domain")
                email_input.mark_processing_completed(False, "Sender domain not allowed")
                return []
            
            events = []
            
            # Process text content
            if email_input.has_text_content():
                text_events = await self._process_text_content(email_input)
                events.extend(text_events)
            
            # Process attachments
            if email_input.has_attachments():
                attachment_events = await self._process_attachments(email_input)
                events.extend(attachment_events)
            
            # Store extracted events in email record
            for event in events:
                event_data = event.dict()
                event_data["source_email_id"] = str(email_input.id)
                email_input.add_extracted_event(event_data)
            
            # Mark processing as completed
            email_input.mark_processing_completed(True)
            
            logger.info(f"Successfully processed email, extracted {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error processing email {email_input.id}: {e}")
            email_input.mark_processing_completed(False, str(e))
            return []
    
    async def _process_text_content(self, email_input: EmailInput) -> List[CalendarEvent]:
        """Process text content of email to extract calendar events."""
        email_input.add_processing_log("text_processing", {"started": True})
        
        try:
            # Prepare text content for processing
            text_content = self._combine_text_content(email_input)
            
            if not text_content.strip():
                return []
            
            # Use calendar agent to extract events from text
            events = await self.calendar_agent.extract_events_from_text(
                text=text_content,
                sender=email_input.sender,
                subject=email_input.subject,
                received_at=email_input.received_at
            )
            
            # Set source email ID for all events
            for event in events:
                event.source_email_id = str(email_input.id)
            
            email_input.add_processing_log("text_processing", {
                "completed": True,
                "events_found": len(events)
            })
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing text content: {e}")
            email_input.add_processing_log("text_processing", {
                "error": str(e)
            })
            return []
    
    async def _process_attachments(self, email_input: EmailInput) -> List[CalendarEvent]:
        """Process email attachments to extract calendar events."""
        email_input.add_processing_log("attachment_processing", {"started": True})
        
        events = []
        
        try:
            # Process image attachments
            image_attachments = email_input.get_attachments_by_type(AttachmentType.IMAGE)
            for attachment in image_attachments:
                try:
                    image_events = await self._process_image_attachment(attachment, email_input)
                    events.extend(image_events)
                    attachment.processed = True
                    attachment.processing_result = {"events_found": len(image_events)}
                except Exception as e:
                    logger.error(f"Error processing image attachment {attachment.filename}: {e}")
                    attachment.processing_result = {"error": str(e)}
            
            # Process audio attachments
            audio_attachments = email_input.get_attachments_by_type(AttachmentType.AUDIO)
            for attachment in audio_attachments:
                try:
                    audio_events = await self._process_audio_attachment(attachment, email_input)
                    events.extend(audio_events)
                    attachment.processed = True
                    attachment.processing_result = {"events_found": len(audio_events)}
                except Exception as e:
                    logger.error(f"Error processing audio attachment {attachment.filename}: {e}")
                    attachment.processing_result = {"error": str(e)}
            
            # Set source email ID for all events
            for event in events:
                event.source_email_id = str(email_input.id)
            
            email_input.add_processing_log("attachment_processing", {
                "completed": True,
                "total_events_found": len(events),
                "images_processed": len(image_attachments),
                "audio_processed": len(audio_attachments)
            })
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing attachments: {e}")
            email_input.add_processing_log("attachment_processing", {
                "error": str(e)
            })
            return []
    
    async def _process_image_attachment(self, attachment, email_input: EmailInput) -> List[CalendarEvent]:
        """Process an image attachment to extract calendar information."""
        if not attachment.file_path:
            return []
        
        try:
            # Use image agent to analyze the image
            extracted_text = await self.image_agent.extract_text_from_image(attachment.file_path)
            
            if not extracted_text.strip():
                return []
            
            # Use calendar agent to extract events from the extracted text
            events = await self.calendar_agent.extract_events_from_text(
                text=extracted_text,
                sender=email_input.sender,
                subject=f"{email_input.subject} (from image: {attachment.filename})",
                received_at=email_input.received_at
            )
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing image attachment: {e}")
            return []
    
    async def _process_audio_attachment(self, attachment, email_input: EmailInput) -> List[CalendarEvent]:
        """Process an audio attachment to extract calendar information."""
        if not attachment.file_path:
            return []
        
        try:
            # Use voice agent to transcribe the audio
            transcribed_text = await self.voice_agent.transcribe_audio(attachment.file_path)
            
            if not transcribed_text.strip():
                return []
            
            # Use calendar agent to extract events from the transcribed text
            events = await self.calendar_agent.extract_events_from_text(
                text=transcribed_text,
                sender=email_input.sender,
                subject=f"{email_input.subject} (from audio: {attachment.filename})",
                received_at=email_input.received_at
            )
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing audio attachment: {e}")
            return []
    
    def _combine_text_content(self, email_input: EmailInput) -> str:
        """Combine text and HTML content into a single text string."""
        content_parts = []
        
        # Add subject as context
        if email_input.subject:
            content_parts.append(f"Subject: {email_input.subject}")
        
        # Add text body
        if email_input.body_text:
            content_parts.append(email_input.body_text)
        
        # Add HTML body (if no text body, or as additional context)
        if email_input.body_html and not email_input.body_text:
            # Simple HTML to text conversion (remove tags)
            import re
            html_text = re.sub(r'<[^>]+>', '', email_input.body_html)
            content_parts.append(html_text)
        
        return "\n\n".join(content_parts)
    
    def calculate_processing_confidence(self, email_input: EmailInput) -> float:
        """Calculate overall confidence score for the email processing."""
        if not email_input.extracted_events:
            return 0.0
        
        # Basic confidence calculation based on:
        # - Number of events found
        # - AI confidence scores
        # - Content quality indicators
        
        total_confidence = 0.0
        event_count = len(email_input.extracted_events)
        
        for event_data in email_input.extracted_events:
            ai_confidence = event_data.get("ai_confidence", 0.5)
            total_confidence += ai_confidence
        
        average_confidence = total_confidence / event_count if event_count > 0 else 0.0
        
        # Adjust based on content quality
        quality_multiplier = 1.0
        
        if email_input.has_text_content():
            quality_multiplier += 0.1
        
        if email_input.has_attachments():
            quality_multiplier += 0.1
        
        final_confidence = min(1.0, average_confidence * quality_multiplier)
        
        email_input.confidence_score = final_confidence
        return final_confidence
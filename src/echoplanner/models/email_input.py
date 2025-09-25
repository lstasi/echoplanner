"""Email input data models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class AttachmentType(str, Enum):
    """Types of email attachments."""
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class EmailAttachment(BaseModel):
    """Represents an email attachment."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the attachment")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size: int = Field(..., ge=0, description="File size in bytes")
    attachment_type: AttachmentType = Field(..., description="Type of attachment")
    file_path: Optional[str] = Field(None, description="Local file path where attachment is stored")
    processed: bool = Field(default=False, description="Whether attachment has been processed")
    processing_result: dict = Field(default_factory=dict, description="Results from processing this attachment")
    
    @validator('attachment_type', pre=True)
    def determine_attachment_type(cls, v, values):
        """Determine attachment type from content type if not explicitly set."""
        if 'content_type' in values:
            content_type = values['content_type'].lower()
            if content_type.startswith('image/'):
                return AttachmentType.IMAGE
            elif content_type.startswith('audio/'):
                return AttachmentType.AUDIO
            elif content_type.startswith('application/') or content_type.startswith('text/'):
                return AttachmentType.DOCUMENT
        return AttachmentType.OTHER


class EmailInput(BaseModel):
    """Represents an incoming email to be processed."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the email")
    message_id: str = Field(..., description="Email message ID from the mail server")
    sender: str = Field(..., description="Email sender address")
    subject: str = Field(..., description="Email subject line")
    body_text: Optional[str] = Field(None, description="Plain text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email")
    received_at: datetime = Field(..., description="When the email was received")
    attachments: List[EmailAttachment] = Field(default_factory=list, description="Email attachments")
    
    # Processing status
    processed: bool = Field(default=False, description="Whether email has been processed")
    processing_started_at: Optional[datetime] = Field(None, description="When processing started")
    processing_completed_at: Optional[datetime] = Field(None, description="When processing completed")
    processing_error: Optional[str] = Field(None, description="Error message if processing failed")
    
    # AI extraction results
    extracted_events: List[dict] = Field(default_factory=list, description="Calendar events extracted from this email")
    family_members_mentioned: List[str] = Field(default_factory=list, description="Family member names mentioned")
    ai_processing_log: List[dict] = Field(default_factory=list, description="Log of AI processing steps")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall AI processing confidence")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the email record was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @validator('sender')
    def validate_sender(cls, v):
        """Validate sender email format."""
        if '@' not in v:
            raise ValueError('Invalid sender email format')
        return v.lower().strip()
    
    @validator('subject', 'body_text')
    def strip_whitespace(cls, v):
        """Strip whitespace from text fields."""
        return v.strip() if v else v
    
    def has_text_content(self) -> bool:
        """Check if email has any text content."""
        return bool(self.body_text or self.body_html)
    
    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return len(self.attachments) > 0
    
    def get_attachments_by_type(self, attachment_type: AttachmentType) -> List[EmailAttachment]:
        """Get attachments of a specific type."""
        return [att for att in self.attachments if att.attachment_type == attachment_type]
    
    def mark_processing_started(self) -> None:
        """Mark email as processing started."""
        self.processing_started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_processing_completed(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark email processing as completed."""
        self.processed = success
        self.processing_completed_at = datetime.utcnow()
        if error_message:
            self.processing_error = error_message
        self.updated_at = datetime.utcnow()
    
    def add_extracted_event(self, event_data: dict) -> None:
        """Add an extracted calendar event."""
        self.extracted_events.append(event_data)
        self.updated_at = datetime.utcnow()
    
    def add_processing_log(self, step: str, result: dict) -> None:
        """Add a processing log entry."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step,
            "result": result
        }
        self.ai_processing_log.append(log_entry)
        self.updated_at = datetime.utcnow()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
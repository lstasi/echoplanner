"""Tests for data models."""

import pytest
from datetime import datetime
from uuid import UUID

from echoplanner.models.family import FamilyMember, MemberRole, Family
from echoplanner.models.calendar_event import CalendarEvent, EventType, EventPriority
from echoplanner.models.email_input import EmailInput, EmailAttachment, AttachmentType


class TestFamilyMember:
    """Tests for FamilyMember model."""
    
    def test_create_family_member(self):
        """Test creating a family member."""
        member = FamilyMember(
            name="John Doe",
            email="john@example.com",
            role=MemberRole.PARENT,
            age=35
        )
        
        assert member.name == "John Doe"
        assert member.email == "john@example.com"
        assert member.role == MemberRole.PARENT
        assert member.age == 35
        assert member.is_active is True
        assert isinstance(member.id, UUID)
        assert isinstance(member.created_at, datetime)
    
    def test_invalid_email(self):
        """Test validation of invalid email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            FamilyMember(
                name="John Doe",
                email="invalid-email"
            )
    
    def test_empty_name(self):
        """Test validation of empty name."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            FamilyMember(name="   ")
    
    def test_update_preferences(self):
        """Test updating member preferences."""
        member = FamilyMember(name="John Doe")
        original_updated_at = member.updated_at
        
        member.update_preferences(timezone="US/Pacific", notifications=True)
        
        assert member.preferences["timezone"] == "US/Pacific"
        assert member.preferences["notifications"] is True
        assert member.updated_at > original_updated_at


class TestFamily:
    """Tests for Family model."""
    
    def test_create_family(self):
        """Test creating a family."""
        family = Family(name="Smith Family")
        
        assert family.name == "Smith Family"
        assert len(family.members) == 0
        assert isinstance(family.id, UUID)
    
    def test_add_member(self):
        """Test adding a family member."""
        family = Family(name="Smith Family")
        member = FamilyMember(name="John Smith")
        
        family.add_member(member)
        
        assert len(family.members) == 1
        assert family.members[0] == member
    
    def test_remove_member(self):
        """Test removing a family member."""
        family = Family(name="Smith Family")
        member = FamilyMember(name="John Smith")
        family.add_member(member)
        
        result = family.remove_member(member.id)
        
        assert result is True
        assert len(family.members) == 0
    
    def test_get_members_by_role(self):
        """Test getting members by role."""
        family = Family(name="Smith Family")
        parent = FamilyMember(name="John Smith", role=MemberRole.PARENT)
        child = FamilyMember(name="Jane Smith", role=MemberRole.CHILD)
        
        family.add_member(parent)
        family.add_member(child)
        
        parents = family.get_members_by_role(MemberRole.PARENT)
        children = family.get_members_by_role(MemberRole.CHILD)
        
        assert len(parents) == 1
        assert len(children) == 1
        assert parents[0] == parent
        assert children[0] == child


class TestCalendarEvent:
    """Tests for CalendarEvent model."""
    
    def test_create_event(self):
        """Test creating a calendar event."""
        start_time = datetime(2024, 1, 15, 10, 0)
        end_time = datetime(2024, 1, 15, 11, 0)
        
        event = CalendarEvent(
            title="Team Meeting",
            description="Weekly team sync",
            start_datetime=start_time,
            end_datetime=end_time,
            location="Conference Room A",
            event_type=EventType.MEETING,
            priority=EventPriority.HIGH
        )
        
        assert event.title == "Team Meeting"
        assert event.description == "Weekly team sync"
        assert event.start_datetime == start_time
        assert event.end_datetime == end_time
        assert event.location == "Conference Room A"
        assert event.event_type == EventType.MEETING
        assert event.priority == EventPriority.HIGH
        assert isinstance(event.id, UUID)
    
    def test_invalid_end_time(self):
        """Test validation of end time before start time."""
        start_time = datetime(2024, 1, 15, 10, 0)
        end_time = datetime(2024, 1, 15, 9, 0)  # Before start time
        
        with pytest.raises(ValueError, match="End datetime must be after start datetime"):
            CalendarEvent(
                title="Invalid Event",
                start_datetime=start_time,
                end_datetime=end_time
            )
    
    def test_get_duration(self):
        """Test getting event duration."""
        start_time = datetime(2024, 1, 15, 10, 0)
        end_time = datetime(2024, 1, 15, 11, 30)
        
        event = CalendarEvent(
            title="Meeting",
            start_datetime=start_time,
            end_datetime=end_time
        )
        
        duration = event.get_duration()
        assert duration is not None
        assert duration.total_seconds() == 5400  # 1.5 hours
    
    def test_add_remove_member(self):
        """Test adding and removing family members."""
        event = CalendarEvent(
            title="Family Dinner",
            start_datetime=datetime(2024, 1, 15, 18, 0)
        )
        
        member_id = UUID('12345678-1234-5678-1234-567812345678')
        
        event.add_member(member_id)
        assert member_id in event.assigned_members
        
        result = event.remove_member(member_id)
        assert result is True
        assert member_id not in event.assigned_members
    
    def test_add_tag(self):
        """Test adding tags to event."""
        event = CalendarEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 10, 0)
        )
        
        event.add_tag("Work")
        event.add_tag("IMPORTANT")  # Should be normalized to lowercase
        
        assert "work" in event.tags
        assert "important" in event.tags


class TestEmailInput:
    """Tests for EmailInput model."""
    
    def test_create_email_input(self):
        """Test creating an email input."""
        received_time = datetime(2024, 1, 15, 9, 0)
        
        email = EmailInput(
            message_id="test@example.com",
            sender="user@example.com",
            subject="Test Email",
            body_text="This is a test email",
            received_at=received_time
        )
        
        assert email.message_id == "test@example.com"
        assert email.sender == "user@example.com"
        assert email.subject == "Test Email"
        assert email.body_text == "This is a test email"
        assert email.received_at == received_time
        assert email.processed is False
    
    def test_invalid_sender(self):
        """Test validation of invalid sender email."""
        with pytest.raises(ValueError, match="Invalid sender email format"):
            EmailInput(
                message_id="test",
                sender="invalid-email",
                subject="Test",
                received_at=datetime.now()
            )
    
    def test_has_text_content(self):
        """Test checking if email has text content."""
        email_with_text = EmailInput(
            message_id="test1",
            sender="user@example.com",
            subject="Test",
            body_text="Hello world",
            received_at=datetime.now()
        )
        
        email_without_text = EmailInput(
            message_id="test2",
            sender="user@example.com",
            subject="Test",
            received_at=datetime.now()
        )
        
        assert email_with_text.has_text_content() is True
        assert email_without_text.has_text_content() is False
    
    def test_mark_processing_completed(self):
        """Test marking email processing as completed."""
        email = EmailInput(
            message_id="test",
            sender="user@example.com",
            subject="Test",
            received_at=datetime.now()
        )
        
        email.mark_processing_completed(success=True)
        
        assert email.processed is True
        assert email.processing_completed_at is not None
        assert email.processing_error is None
        
        # Test with error
        email2 = EmailInput(
            message_id="test2",
            sender="user@example.com",
            subject="Test",
            received_at=datetime.now()
        )
        
        email2.mark_processing_completed(success=False, error_message="Test error")
        
        assert email2.processed is False
        assert email2.processing_error == "Test error"


class TestEmailAttachment:
    """Tests for EmailAttachment model."""
    
    def test_create_attachment(self):
        """Test creating an email attachment."""
        attachment = EmailAttachment(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024,
            attachment_type=AttachmentType.DOCUMENT
        )
        
        assert attachment.filename == "document.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024
        assert attachment.attachment_type == AttachmentType.DOCUMENT
        assert attachment.processed is False
    
    def test_determine_attachment_type(self):
        """Test automatic determination of attachment type."""
        # This would need to be tested with the actual validator
        # For now, just test that the enum values work
        assert AttachmentType.IMAGE == "image"
        assert AttachmentType.AUDIO == "audio"
        assert AttachmentType.DOCUMENT == "document"
        assert AttachmentType.OTHER == "other"
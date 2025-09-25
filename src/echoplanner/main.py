"""Main application class for EchoPlanner."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from .calendar.mcp_connector import MCPConnector
from .calendar.storage import CalendarStorage
from .config.settings import Settings
from .email.client import EmailClient
from .email.processor import EmailProcessor
from .models.calendar_event import CalendarEvent
from .models.email_input import EmailInput
from .models.family import Family

logger = logging.getLogger(__name__)


class EchoPlannerApp:
    """Main application class that coordinates all components."""
    
    def __init__(self, settings: Settings):
        """Initialize the EchoPlanner application."""
        self.settings = settings
        self.storage = CalendarStorage(settings)
        self.family: Optional[Family] = None
        self.email_client: Optional[EmailClient] = None
        self.email_processor: Optional[EmailProcessor] = None
        self.mcp_connector: Optional[MCPConnector] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize all application components."""
        try:
            logger.info("Initializing EchoPlanner application...")
            
            # Load family data
            self.family = await self.storage.load_family()
            if not self.family:
                raise RuntimeError("Failed to load or create family data")
            
            # Initialize email components
            self.email_client = EmailClient(self.settings)
            self.email_processor = EmailProcessor(self.settings, self.family)
            
            # Initialize MCP connector if configured
            if self.settings.mcp_server_url:
                self.mcp_connector = MCPConnector(self.settings)
            else:
                logger.warning("MCP connector not configured, calendar sync disabled")
            
            logger.info("EchoPlanner application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up application resources."""
        try:
            self._running = False
            
            if self.email_client:
                self.email_client.disconnect()
            
            if self.mcp_connector:
                await self.mcp_connector.__aexit__(None, None, None)
            
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def start_email_processing(self) -> None:
        """Start continuous email processing loop."""
        self._running = True
        
        logger.info("Starting continuous email processing...")
        
        while self._running:
            try:
                await self.process_emails_once(dry_run=False)
                
                # Wait for the configured interval before next check
                await asyncio.sleep(self.settings.email_check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping email processing")
                break
            except Exception as e:
                logger.error(f"Error in email processing loop: {e}")
                # Wait a bit before retrying to avoid rapid failure loops
                await asyncio.sleep(60)
    
    async def process_emails_once(self, dry_run: bool = False) -> List[CalendarEvent]:
        """Process emails once and return extracted events."""
        logger.info("Checking for new emails...")
        
        all_extracted_events = []
        
        try:
            # Connect to email server
            if not self.email_client.connect():
                logger.error("Failed to connect to email server")
                return all_extracted_events
            
            # Fetch unread emails
            emails = self.email_client.fetch_unread_emails()
            
            if not emails:
                logger.info("No new emails found")
                return all_extracted_events
            
            logger.info(f"Found {len(emails)} new emails to process")
            
            # Process each email
            for email_input in emails:
                try:
                    extracted_events = await self._process_single_email(email_input, dry_run)
                    all_extracted_events.extend(extracted_events)
                    
                    # Mark email as read after processing
                    # Note: This assumes email_input has some way to identify the original email
                    # In a real implementation, you'd need to track the email ID
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_input.id}: {e}")
                    continue
            
            logger.info(f"Processed {len(emails)} emails, extracted {len(all_extracted_events)} events")
            
        except Exception as e:
            logger.error(f"Error in email processing: {e}")
        finally:
            # Always disconnect from email server
            if self.email_client:
                self.email_client.disconnect()
        
        return all_extracted_events
    
    async def _process_single_email(self, email_input: EmailInput, dry_run: bool = False) -> List[CalendarEvent]:
        """Process a single email and extract calendar events."""
        logger.info(f"Processing email: {email_input.subject}")
        
        extracted_events = []
        
        try:
            # Process email using email processor
            events = await self.email_processor.process_email(email_input)
            
            if not events:
                logger.info("No calendar events extracted from email")
                return extracted_events
            
            logger.info(f"Extracted {len(events)} calendar events from email")
            
            if dry_run:
                logger.info("Dry run mode: not saving events to storage or calendar")
                return events
            
            # Save events to local storage
            for event in events:
                success = await self.storage.save_event(event)
                if success:
                    extracted_events.append(event)
                    logger.info(f"Saved event to local storage: {event.title}")
                else:
                    logger.error(f"Failed to save event to local storage: {event.title}")
            
            # Sync with external calendar via MCP if configured
            if self.mcp_connector:
                for event in extracted_events:
                    try:
                        success = await self.mcp_connector.create_event(event)
                        if success:
                            logger.info(f"Synced event to external calendar: {event.title}")
                        else:
                            logger.warning(f"Failed to sync event to external calendar: {event.title}")
                    except Exception as e:
                        logger.error(f"Error syncing event {event.title}: {e}")
            
            # Save processed email information
            email_data = {
                "id": str(email_input.id),
                "sender": email_input.sender,
                "subject": email_input.subject,
                "processed_at": datetime.utcnow().isoformat(),
                "events_extracted": len(extracted_events),
                "confidence_score": email_input.confidence_score
            }
            await self.storage.save_processed_email(email_data)
            
        except Exception as e:
            logger.error(f"Error processing email {email_input.id}: {e}")
        
        return extracted_events
    
    async def get_events(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        member_id: Optional[str] = None
    ) -> List[CalendarEvent]:
        """Get calendar events with optional filtering."""
        try:
            if start_date and end_date:
                events = await self.storage.get_events_by_date_range(start_date, end_date)
            elif member_id:
                from uuid import UUID  
                events = await self.storage.get_events_by_member(UUID(member_id))
            else:
                events = await self.storage.load_events()
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
    
    async def create_event(self, event: CalendarEvent, sync_to_external: bool = True) -> bool:
        """Create a new calendar event."""
        try:
            # Save to local storage
            success = await self.storage.save_event(event)
            if not success:
                return False
            
            logger.info(f"Created event in local storage: {event.title}")
            
            # Sync to external calendar if configured and requested
            if sync_to_external and self.mcp_connector:
                try:
                    sync_success = await self.mcp_connector.create_event(event)
                    if sync_success:
                        logger.info(f"Synced event to external calendar: {event.title}")
                    else:
                        logger.warning(f"Failed to sync event to external calendar: {event.title}")
                except Exception as e:
                    logger.error(f"Error syncing event to external calendar: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False
    
    async def update_event(self, event: CalendarEvent, sync_to_external: bool = True) -> bool:
        """Update an existing calendar event."""
        try:
            # Update in local storage
            success = await self.storage.save_event(event)
            if not success:
                return False
            
            logger.info(f"Updated event in local storage: {event.title}")
            
            # Sync to external calendar if configured and requested
            if sync_to_external and self.mcp_connector:
                try:
                    sync_success = await self.mcp_connector.update_event(event)
                    if sync_success:
                        logger.info(f"Synced updated event to external calendar: {event.title}")
                    else:
                        logger.warning(f"Failed to sync updated event to external calendar: {event.title}")
                except Exception as e:
                    logger.error(f"Error syncing updated event to external calendar: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return False
    
    async def delete_event(self, event_id: str, sync_to_external: bool = True) -> bool:
        """Delete a calendar event."""
        try:
            from uuid import UUID
            event_uuid = UUID(event_id)
            
            # Delete from local storage
            success = await self.storage.delete_event(event_uuid)
            if not success:
                return False
            
            logger.info(f"Deleted event from local storage: {event_id}")
            
            # Sync deletion to external calendar if configured and requested
            if sync_to_external and self.mcp_connector:
                try:
                    sync_success = await self.mcp_connector.delete_event(event_uuid)
                    if sync_success:
                        logger.info(f"Synced event deletion to external calendar: {event_id}")
                    else:
                        logger.warning(f"Failed to sync event deletion to external calendar: {event_id}")
                except Exception as e:
                    logger.error(f"Error syncing event deletion to external calendar: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False
    
    async def get_family_members(self) -> List[dict]:
        """Get family members information."""
        try:
            if not self.family:
                return []
            
            members_data = []
            for member in self.family.members:
                members_data.append({
                    "id": str(member.id),
                    "name": member.name,
                    "email": member.email,
                    "role": member.role.value,
                    "age": member.age,
                    "is_active": member.is_active
                })
            
            return members_data
            
        except Exception as e:
            logger.error(f"Error getting family members: {e}")
            return []
    
    async def get_application_stats(self) -> dict:
        """Get application statistics and status."""
        try:
            storage_stats = await self.storage.get_storage_stats()
            
            stats = {
                "application": {
                    "name": "EchoPlanner",
                    "version": "0.1.0",
                    "running": self._running
                },
                "storage": storage_stats,
                "configuration": {
                    "email_configured": bool(self.settings.email_host and self.settings.email_username),
                    "ai_configured": bool(self.settings.openai_api_key),
                    "mcp_configured": bool(self.settings.mcp_server_url),
                    "email_check_interval": self.settings.email_check_interval,
                    "max_concurrent_emails": self.settings.max_concurrent_emails
                },
                "family": {
                    "name": self.family.name if self.family else "Unknown",
                    "member_count": len(self.family.members) if self.family else 0
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting application stats: {e}")
            return {"error": str(e)}
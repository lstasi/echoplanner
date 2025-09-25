"""Email client for receiving emails via IMAP."""

import email
import imaplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from ..config.settings import Settings
from ..models.email_input import AttachmentType, EmailAttachment, EmailInput

logger = logging.getLogger(__name__)


class EmailClient:
    """Email client for connecting to and retrieving emails from IMAP server."""
    
    def __init__(self, settings: Settings):
        """Initialize email client with settings."""
        self.settings = settings
        self.connection: Optional[imaplib.IMAP4_SSL] = None
    
    def connect(self) -> bool:
        """Connect to the email server."""
        try:
            if self.settings.email_use_ssl:
                self.connection = imaplib.IMAP4_SSL(
                    self.settings.email_host, 
                    self.settings.email_port
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.settings.email_host, 
                    self.settings.email_port
                )
            
            self.connection.login(
                self.settings.email_username,
                self.settings.email_password
            )
            logger.info("Successfully connected to email server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            self.connection = None
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the email server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.error(f"Error disconnecting from email server: {e}")
            finally:
                self.connection = None
    
    def fetch_unread_emails(self, folder: str = "INBOX") -> List[EmailInput]:
        """Fetch unread emails from the specified folder."""
        if not self.connection:
            logger.error("Not connected to email server")
            return []
        
        try:
            self.connection.select(folder)
            
            # Search for unread emails
            status, messages = self.connection.search(None, "UNSEEN")
            if status != "OK":
                logger.error(f"Failed to search for emails: {status}")
                return []
            
            email_ids = messages[0].split()
            emails = []
            
            for email_id in email_ids:
                try:
                    email_input = self._fetch_email_by_id(email_id.decode())
                    if email_input:
                        emails.append(email_input)
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} unread emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
            return []
    
    def _fetch_email_by_id(self, email_id: str) -> Optional[EmailInput]:
        """Fetch a specific email by ID."""
        if not self.connection:
            return None
        
        try:
            status, msg_data = self.connection.fetch(email_id, "(RFC822)")
            if status != "OK":
                logger.error(f"Failed to fetch email {email_id}")
                return None
            
            email_message = email.message_from_bytes(msg_data[0][1])
            return self._parse_email_message(email_message, email_id)
            
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None
    
    def _parse_email_message(self, email_message: email.message.Message, email_id: str) -> EmailInput:
        """Parse an email message into EmailInput object."""
        # Extract basic email information
        sender = email_message.get("From", "")
        subject = email_message.get("Subject", "")
        date_str = email_message.get("Date", "")
        message_id = email_message.get("Message-ID", f"echoplanner-{uuid4()}")
        
        # Parse received date
        try:
            received_at = email.utils.parsedate_to_datetime(date_str)
        except Exception:
            received_at = datetime.utcnow()
        
        # Extract email body
        body_text, body_html = self._extract_body(email_message)
        
        # Process attachments
        attachments = self._process_attachments(email_message)
        
        return EmailInput(
            message_id=message_id,
            sender=sender,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            received_at=received_at,
            attachments=attachments
        )
    
    def _extract_body(self, email_message: email.message.Message) -> Tuple[Optional[str], Optional[str]]:
        """Extract text and HTML body from email message."""
        body_text = None
        body_html = None
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain" and body_text is None:
                    try:
                        body_text = part.get_payload(decode=True).decode("utf-8")
                    except Exception as e:
                        logger.warning(f"Failed to decode text body: {e}")
                
                elif content_type == "text/html" and body_html is None:
                    try:
                        body_html = part.get_payload(decode=True).decode("utf-8")
                    except Exception as e:
                        logger.warning(f"Failed to decode HTML body: {e}")
        else:
            # Non-multipart message
            content_type = email_message.get_content_type()
            try:
                payload = email_message.get_payload(decode=True).decode("utf-8")
                if content_type == "text/plain":
                    body_text = payload
                elif content_type == "text/html":
                    body_html = payload
            except Exception as e:
                logger.warning(f"Failed to decode message body: {e}")
        
        return body_text, body_html
    
    def _process_attachments(self, email_message: email.message.Message) -> List[EmailAttachment]:
        """Process and save email attachments."""
        attachments = []
        
        if not email_message.is_multipart():
            return attachments
        
        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    try:
                        attachment = self._save_attachment(part, filename)
                        if attachment:
                            attachments.append(attachment)
                    except Exception as e:
                        logger.error(f"Failed to process attachment {filename}: {e}")
        
        return attachments
    
    def _save_attachment(self, part: email.message.Message, filename: str) -> Optional[EmailAttachment]:
        """Save an email attachment to disk."""
        try:
            # Generate unique filename to avoid conflicts
            unique_filename = f"{uuid4()}_{filename}"
            file_path = self.settings.get_attachment_path(unique_filename)
            
            # Get attachment data
            attachment_data = part.get_payload(decode=True)
            if not attachment_data:
                return None
            
            # Check file size
            if len(attachment_data) > self.settings.max_attachment_size:
                logger.warning(f"Attachment {filename} exceeds size limit")
                return None
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(attachment_data)
            
            # Determine attachment type
            content_type = part.get_content_type() or "application/octet-stream"
            
            return EmailAttachment(
                filename=filename,
                content_type=content_type,
                size=len(attachment_data),
                attachment_type=self._determine_attachment_type(content_type),
                file_path=str(file_path)
            )
            
        except Exception as e:
            logger.error(f"Failed to save attachment {filename}: {e}")
            return None
    
    def _determine_attachment_type(self, content_type: str) -> AttachmentType:
        """Determine attachment type from content type."""
        content_type = content_type.lower()
        
        if content_type.startswith("image/"):
            return AttachmentType.IMAGE
        elif content_type.startswith("audio/"):
            return AttachmentType.AUDIO
        elif content_type.startswith(("application/", "text/")):
            return AttachmentType.DOCUMENT
        else:
            return AttachmentType.OTHER
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark an email as read."""
        if not self.connection:
            return False
        
        try:
            self.connection.store(email_id, "+FLAGS", "\\Seen")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email {email_id} as read: {e}")
            return False
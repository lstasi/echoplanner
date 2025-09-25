"""Email utility functions."""

import re
from typing import List, Optional


def extract_email_domain(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email or '@' not in email:
        return None
    
    return email.split('@')[-1].lower().strip()


def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text."""
    if not text:
        return []
    
    # Email regex pattern
    pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    emails = re.findall(pattern, text)
    
    # Validate and deduplicate
    valid_emails = []
    seen = set()
    
    for email in emails:
        email_lower = email.lower()
        if email_lower not in seen and is_valid_email(email):
            valid_emails.append(email)
            seen.add(email_lower)
    
    return valid_emails


def clean_email_content(content: str) -> str:
    """Clean email content by removing common artifacts."""
    if not content:
        return ""
    
    # Remove common email artifacts
    content = re.sub(r'On .* wrote:', '', content)  # Remove forwarded message headers
    content = re.sub(r'From:.*?Subject:.*?\n', '', content, flags=re.DOTALL)  # Remove email headers
    content = re.sub(r'-----Original Message-----.*', '', content, flags=re.DOTALL)  # Remove original message
    content = re.sub(r'________________________________.*', '', content, flags=re.DOTALL)  # Remove separators
    
    # Remove excessive whitespace
    content = re.sub(r'\n\s*\n', '\n\n', content)  # Multiple line breaks
    content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces/tabs
    
    return content.strip()


def extract_quoted_content(content: str) -> str:
    """Extract only the quoted/main content, removing replies and forwards."""
    if not content:
        return ""
    
    # Common patterns that indicate quoted content
    quote_patterns = [
        r'(?i)on .* wrote:.*$',
        r'(?i)from:.*?sent:.*?to:.*?subject:.*?\n',
        r'(?i)-----original message-----.*$',
        r'(?i)>.*$',  # Lines starting with >
        r'(?i)________________________________.*$'
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that match quote patterns
        is_quoted = False
        for pattern in quote_patterns:
            if re.search(pattern, line, re.MULTILINE | re.DOTALL):
                is_quoted = True
                break
        
        if not is_quoted:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def extract_sender_name(sender: str) -> Optional[str]:
    """Extract sender name from email address or display name."""
    if not sender:
        return None
    
    # Check if sender has display name format "Name <email@domain.com>"
    match = re.match(r'^(.+?)\s*<.+@.+>$', sender)
    if match:
        name = match.group(1).strip()
        # Remove quotes if present
        name = name.strip('"\'')
        return name if name else None
    
    # If just email address, try to extract name from local part
    if '@' in sender:
        local_part = sender.split('@')[0]
        # Replace common separators with spaces
        name = re.sub(r'[._-]', ' ', local_part)
        # Capitalize words
        name = ' '.join(word.capitalize() for word in name.split())
        return name if name and not name.isdigit() else None
    
    return sender.strip() if sender.strip() else None


def is_automated_email(sender: str, subject: str, content: str) -> bool:
    """Detect if email is likely automated/system generated."""
    if not sender:
        return False
    
    # Common automated sender patterns
    automated_patterns = [
        r'noreply',
        r'no-reply',
        r'donotreply',
        r'system',
        r'admin',
        r'notification',
        r'alert',
        r'robot',
        r'bot'
    ]
    
    sender_lower = sender.lower()
    for pattern in automated_patterns:
        if pattern in sender_lower:
            return True
    
    # Check subject for automated patterns
    if subject:
        subject_lower = subject.lower()
        automated_subject_patterns = [
            r'unsubscribe',
            r'delivery failure',
            r'mail delivery',
            r'auto.?reply',
            r'out of office',
            r'vacation'
        ]
        
        for pattern in automated_subject_patterns:
            if re.search(pattern, subject_lower):
                return True
    
    # Check content for automated patterns
    if content:
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in [
            'this is an automated message',
            'do not reply to this email',
            'automatically generated',
            'unsubscribe'
        ]):
            return True
    
    return False
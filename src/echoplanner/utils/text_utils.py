"""Text processing utility functions."""

import re
from typing import List, Set


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Fix common encoding issues
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 20) -> List[str]:
    """Extract meaningful keywords from text."""
    if not text:
        return []
    
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter words
    keywords = []
    for word in words:
        if (len(word) >= min_length and 
            word not in stop_words and 
            not word.isdigit()):
            keywords.append(word)
    
    # Count frequency and get most common
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_keywords[:max_keywords]]


def extract_time_references(text: str) -> List[str]:
    """Extract time-related references from text."""
    if not text:
        return []
    
    time_patterns = [
        r'\b\d{1,2}:\d{2}\s*(?:am|pm)?\b',  # Times like 3:30, 3:30pm
        r'\b\d{1,2}\s*(?:am|pm)\b',        # Times like 3pm
        r'\b(?:morning|afternoon|evening|night)\b',  # Time of day
        r'\b(?:today|tomorrow|yesterday)\b',  # Relative days
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',  # Days of week
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',  # Months
        r'\b\d{1,2}\/\d{1,2}\/\d{4}\b',    # Dates like 12/25/2023
        r'\b\d{1,2}-\d{1,2}-\d{4}\b',     # Dates like 12-25-2023
        r'\bnext\s+(?:week|month|year)\b', # Next week/month/year
        r'\blast\s+(?:week|month|year)\b', # Last week/month/year
    ]
    
    time_refs = []
    text_lower = text.lower()
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text_lower)
        time_refs.extend(matches)
    
    return list(set(time_refs))  # Remove duplicates


def extract_names(text: str) -> List[str]:
    """Extract potential names from text."""
    if not text:
        return []
    
    # Simple name pattern: capitalized words that aren't sentence starters
    sentences = re.split(r'[.!?]+', text)
    names = set()
    
    for sentence in sentences:
        words = sentence.strip().split()
        for i, word in enumerate(words):
            # Skip first word of sentence (likely not a name in this context)
            if i == 0:
                continue
            
            # Look for capitalized words that could be names
            if (word[0].isupper() and 
                len(word) > 1 and 
                word.isalpha() and
                word.lower() not in {'the', 'and', 'or', 'but', 'with', 'for', 'to', 'from'}):
                names.add(word)
    
    return list(names)


def extract_locations(text: str) -> List[str]:
    """Extract potential location references from text."""
    if not text:
        return []
    
    location_patterns = [
        r'\bat\s+([A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd))\b',
        r'\bat\s+([A-Z][a-zA-Z\s]+(?:School|Hospital|Library|Park|Center|Mall|Store))\b',
        r'\bin\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)\b',  # City, State
        r'\b(\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd))\b',  # Street addresses
    ]
    
    locations = []
    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        locations.extend(matches)
    
    return list(set(locations))  # Remove duplicates


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using simple word overlap."""
    if not text1 or not text2:
        return 0.0
    
    # Extract words and normalize
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix."""
    if not text or len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length // 2:  # Only break at word if not too short
        truncated = truncated[:last_space]
    
    return truncated + suffix
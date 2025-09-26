# Agent Framework

## Overview

The Agent Framework provides a flexible system for processing different types of content from email communications. Each agent specializes in a specific content type and extraction method.

## Agent Types

### Calendar Agent
- Processes natural language text to extract calendar events
- Uses AI/LLM models for intelligent parsing
- Handles date/time recognition and family member assignment

### Image Agent
- Performs OCR on image attachments
- Extracts calendar information from screenshots or photos
- Supports multiple image formats

### Voice Agent
- Transcribes audio attachments to text
- Converts speech to calendar events
- Integrates with speech-to-text services

## Agent Interface

All agents implement a common interface for consistency:
- Input processing methods
- Output standardization
- Error handling and logging
- Confidence scoring for extracted data
- Storage integration for context and deduplication

## Context and Memory

### Historical Context
- Access to previous interaction records
- Pattern recognition from stored data
- User behavior learning and adaptation

### Deduplication
- Cross-reference with existing events
- Semantic similarity analysis
- Prevention of duplicate calendar entries
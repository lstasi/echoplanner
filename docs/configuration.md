# Configuration

## Overview

EchoPlanner uses environment-based configuration for security and deployment flexibility. All sensitive data is managed through environment variables.

## Configuration Categories

### Email Settings
- IMAP server connection parameters
- Authentication credentials
- Security and SSL settings

### AI Integration
- OpenRouter API keys and model selection (GPT-4, Claude, Llama, etc.)
- Local LLM configuration and model paths (Ollama, LM Studio)
- Model switching and failover strategies
- Processing parameters and limits
- Fallback options for offline operation

### Calendar Integration
- MCP server endpoints and authentication
- Synchronization settings
- Local storage configuration

### Security Settings
- Encryption keys and secrets
- Access control and domain restrictions
- Data retention and cleanup policies

## Environment Management

- Development and production configurations
- Secret management best practices
- Configuration validation and error handling
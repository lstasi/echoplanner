"""Application settings and configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    app_name: str = Field(default="EchoPlanner", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")
    
    # Email settings
    email_host: str = Field(..., description="Email server host")
    email_port: int = Field(default=993, description="Email server port")
    email_username: str = Field(..., description="Email username")
    email_password: str = Field(..., description="Email password")
    email_use_ssl: bool = Field(default=True, description="Use SSL for email connection")
    email_check_interval: int = Field(default=300, description="Email check interval in seconds")
    
    # AI/LLM settings
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    ai_temperature: float = Field(default=0.1, description="AI temperature setting")
    ai_max_tokens: int = Field(default=1000, description="Maximum tokens for AI responses")
    
    # Calendar/MCP settings
    mcp_server_url: Optional[str] = Field(None, description="MCP server URL for calendar integration")
    mcp_api_key: Optional[str] = Field(None, description="MCP API key")
    calendar_timezone: str = Field(default="UTC", description="Default calendar timezone")
    
    # Storage settings
    data_dir: Path = Field(default=Path("data"), description="Data directory path")
    attachments_dir: Path = Field(default=Path("data/attachments"), description="Attachments directory")
    logs_dir: Path = Field(default=Path("logs"), description="Logs directory")
    
    # Security settings
    secret_key: str = Field(..., description="Secret key for encryption")
    allowed_email_domains: List[str] = Field(default_factory=list, description="Allowed email domains")
    max_attachment_size: int = Field(default=10485760, description="Maximum attachment size in bytes (10MB)")
    
    # Processing settings
    max_concurrent_emails: int = Field(default=5, description="Maximum concurrent email processing")
    retry_attempts: int = Field(default=3, description="Number of retry attempts for failed operations")
    cleanup_days: int = Field(default=30, description="Days to keep processed emails")
    
    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [self.data_dir, self.attachments_dir, self.logs_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def email_config(self) -> dict:
        """Get email configuration as dictionary."""
        return {
            "host": self.email_host,
            "port": self.email_port,
            "username": self.email_username,
            "password": self.email_password,
            "use_ssl": self.email_use_ssl
        }
    
    @property
    def openai_config(self) -> dict:
        """Get OpenAI configuration as dictionary."""
        return {
            "api_key": self.openai_api_key,
            "model": self.openai_model,
            "temperature": self.ai_temperature,
            "max_tokens": self.ai_max_tokens
        }
    
    @property
    def mcp_config(self) -> dict:
        """Get MCP configuration as dictionary."""
        return {
            "server_url": self.mcp_server_url,
            "api_key": self.mcp_api_key
        }
    
    def is_email_domain_allowed(self, email: str) -> bool:
        """Check if email domain is allowed."""
        if not self.allowed_email_domains:
            return True  # If no restrictions, allow all
        
        domain = email.split("@")[-1].lower()
        return domain in [d.lower() for d in self.allowed_email_domains]
    
    def get_attachment_path(self, filename: str) -> Path:
        """Get full path for an attachment file."""
        return self.attachments_dir / filename
    
    def get_log_path(self, log_name: str) -> Path:
        """Get full path for a log file."""
        return self.logs_dir / log_name


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
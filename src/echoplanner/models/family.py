"""Family member data models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class MemberRole(str, Enum):
    """Family member roles."""
    PARENT = "parent"
    CHILD = "child"
    GUARDIAN = "guardian"
    OTHER = "other"


class FamilyMember(BaseModel):
    """Represents a family member in the planning system."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the family member")
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the family member")
    email: Optional[str] = Field(None, description="Email address for notifications")
    role: MemberRole = Field(default=MemberRole.OTHER, description="Role in the family")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age of the family member")
    timezone: str = Field(default="UTC", description="Timezone for the family member")
    preferences: dict = Field(default_factory=dict, description="Personal preferences and settings")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the member was added")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether the member is active in the system")
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip()
    
    def update_preferences(self, **kwargs) -> None:
        """Update member preferences."""
        self.preferences.update(kwargs)
        self.updated_at = datetime.utcnow()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class Family(BaseModel):
    """Represents a family group with members."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the family")
    name: str = Field(..., min_length=1, max_length=100, description="Family name or identifier")
    members: List[FamilyMember] = Field(default_factory=list, description="List of family members")
    settings: dict = Field(default_factory=dict, description="Family-wide settings")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the family was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    def add_member(self, member: FamilyMember) -> None:
        """Add a new family member."""
        if member not in self.members:
            self.members.append(member)
            self.updated_at = datetime.utcnow()
    
    def remove_member(self, member_id: UUID) -> bool:
        """Remove a family member by ID."""
        for i, member in enumerate(self.members):
            if member.id == member_id:
                self.members.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def get_member(self, member_id: UUID) -> Optional[FamilyMember]:
        """Get a family member by ID."""
        for member in self.members:
            if member.id == member_id:
                return member
        return None
    
    def get_members_by_role(self, role: MemberRole) -> List[FamilyMember]:
        """Get all family members with a specific role."""
        return [member for member in self.members if member.role == role]
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
"""FastAPI application for EchoPlanner REST API."""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config.settings import get_settings
from .main import EchoPlannerApp
from .models.calendar_event import CalendarEvent
from .models.family import FamilyMember, MemberRole

# Initialize settings and app
settings = get_settings()
echo_app = EchoPlannerApp(settings)

# Create FastAPI instance
app = FastAPI(
    title="EchoPlanner API",
    description="Family Planner AI Agent Assistant API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests/responses
class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    event_type: str = "other"
    priority: str = "medium"
    assigned_members: List[str] = []
    tags: List[str] = []


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    event_type: Optional[str] = None
    priority: Optional[str] = None
    assigned_members: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class MemberCreate(BaseModel):
    name: str
    email: Optional[str] = None
    role: str = "other"
    age: Optional[int] = None


class ProcessEmailRequest(BaseModel):
    dry_run: bool = False


# Initialize application on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the EchoPlanner application on startup."""
    await echo_app.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up the EchoPlanner application on shutdown."""
    await echo_app.cleanup()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Statistics endpoint
@app.get("/stats")
async def get_stats():
    """Get application statistics."""
    return await echo_app.get_application_stats()


# Events endpoints
@app.get("/events", response_model=List[dict])
async def get_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    member_id: Optional[str] = None
):
    """Get calendar events with optional filtering."""
    events = await echo_app.get_events(start_date, end_date, member_id)
    return [event.dict() for event in events]


@app.post("/events", response_model=dict)
async def create_event(event_data: EventCreate):
    """Create a new calendar event."""
    try:
        # Convert API model to CalendarEvent
        event = CalendarEvent(
            title=event_data.title,
            description=event_data.description,
            start_datetime=event_data.start_datetime,
            end_datetime=event_data.end_datetime,
            all_day=event_data.all_day,
            location=event_data.location,
            event_type=event_data.event_type,
            priority=event_data.priority,
            assigned_members=event_data.assigned_members,
            tags=event_data.tags
        )
        
        success = await echo_app.create_event(event)
        
        if success:
            return {"success": True, "event_id": str(event.id), "message": "Event created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create event")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/events/{event_id}", response_model=dict)
async def update_event(event_id: str, event_data: EventUpdate):
    """Update an existing calendar event."""
    try:
        # Get existing event
        events = await echo_app.get_events()
        existing_event = None
        
        for event in events:
            if str(event.id) == event_id:
                existing_event = event
                break
        
        if not existing_event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update fields
        update_data = event_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(existing_event, field):
                setattr(existing_event, field, value)
        
        existing_event.updated_at = datetime.utcnow()
        
        success = await echo_app.update_event(existing_event)
        
        if success:
            return {"success": True, "message": "Event updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update event")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/events/{event_id}", response_model=dict)
async def delete_event(event_id: str):
    """Delete a calendar event."""
    try:
        success = await echo_app.delete_event(event_id)
        
        if success:
            return {"success": True, "message": "Event deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Event not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Family endpoints
@app.get("/family/members", response_model=List[dict])
async def get_family_members():
    """Get family members."""
    return await echo_app.get_family_members()


@app.post("/family/members", response_model=dict)
async def add_family_member(member_data: MemberCreate):
    """Add a new family member."""
    try:
        member = FamilyMember(
            name=member_data.name,
            email=member_data.email,
            role=MemberRole(member_data.role),
            age=member_data.age
        )
        
        # Add to family
        echo_app.family.add_member(member)
        
        # Save family data
        success = await echo_app.storage.save_family(echo_app.family)
        
        if success:
            return {"success": True, "member_id": str(member.id), "message": "Family member added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save family member")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Email processing endpoints
@app.post("/email/process", response_model=dict)
async def process_emails(request: ProcessEmailRequest, background_tasks: BackgroundTasks):
    """Process emails and extract calendar events."""
    try:
        if request.dry_run:
            # Process immediately for dry run
            events = await echo_app.process_emails_once(dry_run=True)
            return {
                "success": True,
                "message": f"Dry run completed, would have extracted {len(events)} events",
                "events_found": len(events)
            }
        else:
            # Process in background for real processing
            background_tasks.add_task(echo_app.process_emails_once, False)
            return {
                "success": True,
                "message": "Email processing started in background"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/email/status", response_model=dict)
async def get_email_status():
    """Get email processing status."""
    try:
        stats = await echo_app.get_application_stats()
        
        return {
            "configured": stats.get("configuration", {}).get("email_configured", False),
            "check_interval": stats.get("configuration", {}).get("email_check_interval", 0),
            "processed_emails": stats.get("storage", {}).get("processed_emails", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Configuration endpoints
@app.get("/config", response_model=dict)
async def get_configuration():
    """Get application configuration status."""
    try:
        stats = await echo_app.get_application_stats()
        return stats.get("configuration", {})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export endpoints
@app.get("/export/ical")
async def export_ical(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Export events to iCal format."""
    try:
        events = await echo_app.get_events(start_date, end_date)
        
        if echo_app.mcp_connector:
            ical_content = await echo_app.mcp_connector.export_to_ical(events)
        else:
            # Basic iCal export without MCP
            ical_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//EchoPlanner//EN\nEND:VCALENDAR"
        
        return {
            "success": True,
            "ical_content": ical_content,
            "events_count": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
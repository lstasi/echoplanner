"""Command-line interface for EchoPlanner."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .config.settings import get_settings
from .main import EchoPlannerApp

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """EchoPlanner - Family Planner AI Agent Assistant."""
    pass


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind the server to')
@click.option('--port', default=8000, help='Port to bind the server to')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes')
def serve(host: str, port: int, reload: bool):
    """Start the EchoPlanner API server."""
    try:
        import uvicorn
        
        settings = get_settings()
        
        # Override settings with CLI arguments
        actual_host = host if host != '127.0.0.1' else settings.api_host
        actual_port = port if port != 8000 else settings.api_port
        
        logger.info(f"Starting EchoPlanner server on {actual_host}:{actual_port}")
        
        uvicorn.run(
            "echoplanner.api:app",
            host=actual_host,
            port=actual_port,
            reload=reload,
            log_level=settings.log_level.lower()
        )
        
    except ImportError:
        click.echo("Error: uvicorn is required to run the server. Install it with 'pip install uvicorn'")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {e}")
        sys.exit(1)


@cli.command()
@click.option('--check-once', is_flag=True, help='Check emails once and exit')
@click.option('--dry-run', is_flag=True, help='Process emails without saving to calendar')
def process_emails(check_once: bool, dry_run: bool):
    """Process emails and extract calendar events."""
    
    async def run_processing():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            if check_once:
                click.echo("Processing emails (single run)...")
                await app.process_emails_once(dry_run=dry_run)
            else:
                click.echo("Starting continuous email processing... (Press Ctrl+C to stop)")
                await app.start_email_processing()
                
        except KeyboardInterrupt:
            click.echo("\nStopping email processing...")
        except Exception as e:
            click.echo(f"Error processing emails: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(run_processing())


@cli.command()
@click.argument('email_file', type=click.Path(exists=True))
def process_file(email_file: str):
    """Process a single email file (for testing)."""
    
    async def run_file_processing():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            # Process the email file
            email_path = Path(email_file)
            click.echo(f"Processing email file: {email_path}")
            
            # This would need to be implemented in the main app
            # For now, just show that we would process it
            click.echo("File processing not yet implemented")
            
        except Exception as e:
            click.echo(f"Error processing file: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(run_file_processing())


@cli.command()
def setup():
    """Initial setup and configuration."""
    click.echo("EchoPlanner Setup")
    click.echo("================")
    
    settings = get_settings()
    
    # Check required settings
    required_settings = [
        ('EMAIL_HOST', 'Email server host'),
        ('EMAIL_USERNAME', 'Email username'),
        ('EMAIL_PASSWORD', 'Email password'),
        ('SECRET_KEY', 'Secret key for encryption'),
    ]
    
    missing_settings = []
    for env_var, description in required_settings:
        if not getattr(settings, env_var.lower(), None):
            missing_settings.append((env_var, description))
    
    if missing_settings:
        click.echo("Missing required settings:")
        for env_var, description in missing_settings:
            click.echo(f"  {env_var}: {description}")
        click.echo("\nPlease set these environment variables or add them to a .env file")
        return
    
    click.echo("Configuration check passed!")
    
    # Create directories
    click.echo("Creating directories...")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    
    click.echo("Setup completed successfully!")


@cli.command()
def status():
    """Show system status and statistics."""
    
    async def show_status():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            # Get storage statistics
            stats = await app.storage.get_storage_stats()
            
            click.echo("EchoPlanner Status")
            click.echo("==================")
            click.echo(f"Data Directory: {stats.get('data_directory', 'Unknown')}")
            click.echo(f"Total Events: {stats.get('total_events', 0)}")
            click.echo(f"Active Events: {stats.get('active_events', 0)}")
            click.echo(f"Processed Emails: {stats.get('processed_emails', 0)}")
            click.echo(f"Family Members: {stats.get('family_members', 0)}")
            
            # Check file existence
            files = stats.get('files', {})
            click.echo("\nData Files:")
            click.echo(f"  Events: {'✓' if files.get('events_file_exists') else '✗'}")
            click.echo(f"  Family: {'✓' if files.get('family_file_exists') else '✗'}")
            click.echo(f"  Emails: {'✓' if files.get('emails_file_exists') else '✗'}")
            
            # Check configuration
            click.echo("\nConfiguration:")
            click.echo(f"  Email configured: {'✓' if settings.email_host else '✗'}")
            click.echo(f"  OpenAI configured: {'✓' if settings.openai_api_key else '✗'}")
            click.echo(f"  MCP configured: {'✓' if settings.mcp_server_url else '✗'}")
            
        except Exception as e:
            click.echo(f"Error getting status: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(show_status())


@cli.command()
@click.option('--days', default=30, help='Days of data to keep')
def cleanup(days: int):
    """Clean up old data."""
    
    async def run_cleanup():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            click.echo(f"Cleaning up data older than {days} days...")
            await app.storage.cleanup_old_data(days_to_keep=days)
            click.echo("Cleanup completed!")
            
        except Exception as e:
            click.echo(f"Error during cleanup: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(run_cleanup())


@cli.group()
def family():
    """Family member management commands."""
    pass


@family.command('list')
def list_members():
    """List family members."""
    
    async def list_family_members():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            family_data = await app.storage.load_family()
            
            if not family_data or not family_data.members:
                click.echo("No family members found.")
                return
            
            click.echo(f"Family: {family_data.name}")
            click.echo("Members:")
            for member in family_data.members:
                click.echo(f"  - {member.name} ({member.role.value})")
                if member.email:
                    click.echo(f"    Email: {member.email}")
                if member.age:
                    click.echo(f"    Age: {member.age}")
            
        except Exception as e:
            click.echo(f"Error listing family members: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(list_family_members())


@family.command('add')
@click.argument('name')
@click.option('--email', help='Email address')
@click.option('--role', type=click.Choice(['parent', 'child', 'guardian', 'other']), default='other', help='Family role')
@click.option('--age', type=int, help='Age')
def add_member(name: str, email: Optional[str], role: str, age: Optional[int]):
    """Add a family member."""
    
    async def add_family_member():
        try:
            settings = get_settings()
            app = EchoPlannerApp(settings)
            
            await app.initialize()
            
            from .models.family import FamilyMember, MemberRole
            
            member = FamilyMember(
                name=name,
                email=email,
                role=MemberRole(role),
                age=age
            )
            
            family_data = await app.storage.load_family()
            family_data.add_member(member)
            
            success = await app.storage.save_family(family_data)
            
            if success:
                click.echo(f"Added family member: {name}")
            else:
                click.echo("Failed to add family member")
                sys.exit(1)
            
        except Exception as e:
            click.echo(f"Error adding family member: {e}")
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(add_family_member())


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
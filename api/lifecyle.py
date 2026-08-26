"""
Application Lifecycle Management
Handles startup/shutdown events including background scheduler initialization
"""

from contextlib import asynccontextmanager
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan handler for startup and shutdown events.
    
    This function:
    1. Starts background scheduler on application startup
    2. Shuts down scheduler gracefully on application shutdown
    """
    
    # ===== STARTUP PHASE =====
    
    try:
        logger.info("🚀 Starting OpenClaw PR Manager API...")
        
        # Check if scheduler is enabled
        scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
        
        if scheduler_enabled:
            # Initialize APScheduler
            scheduler = BackgroundScheduler(
                timezone='UTC',
                job_defaults={
                    'coalesce': True,
                    # Only one follow-up run may execute at a time. Concurrent
                    # runs can send the same due item more than once.
                    'max_instances': 1,
                    'misfire_grace_time': 60
                }
            )
            
            # Register follow-up processing job (runs every 5 minutes)
            scheduler.add_job(
                func=process_follow_ups_job,
                trigger=CronTrigger(minute='*/5'),  # Every 5 minutes
                id='follow_up_processor',
                name='Process due follow-ups',
                replace_existing=True
            )

            # Register reply sync job (runs every 5 minutes)
            scheduler.add_job(
                func=sync_replies_job,
                trigger=CronTrigger(minute='*/5'),  # Every 5 minutes
                id='reply_sync_processor',
                name='Sync Gmail replies',
                replace_existing=True
            )
            
            # Start scheduler
            scheduler.start()
            logger.info(f"⏰ Background scheduler started (follow-up & reply sync)")
            
            # Store scheduler reference in app state
            app.state.scheduler = scheduler
        
        else:
            logger.warning("⏰ Background scheduler disabled (SCHEDULER_ENABLED=false)")
        
        # Log environment status
        logger.info("📊 Application initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    # ===== SHUTDOWN PHASE =====
    
    try:
        logger.info("🛑 Shutting down OpenClaw PR Manager API...")
        
        # Gracefully shutdown scheduler
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler:
            scheduler.shutdown(wait=True)
            logger.info("✅ Scheduler shutdown complete")
        
        logger.info("✅ Shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


def process_follow_ups_job():
    """
    Job function to process all due follow-up emails.
    
    Called by scheduler every 5 minutes when enabled.
    Handles:
    - Initial pitches not sent yet
    - Follow-up reminders at appropriate intervals
    - Breakup messages when no response received
    """
    
    from services.scheduler.follow_up import FollowUpScheduler
    
    try:
        logger.info("▶️  Starting follow-up processing job...")
        
        result = FollowUpScheduler().process_due_follow_ups()
        
        logger.info(f"✅ Follow-up job completed: {result}")
        
        return {"processed": len(result), "details": result}
        
    except Exception as e:
        logger.error(f"❌ Follow-up job failed: {e}", exc_info=True)
        
        # In production, send alert/notification here
        # For now, just log the error
        
        return {"error": str(e), "processed": 0}


def sync_replies_job():
    """Job function to auto-detect incoming replies from Gmail threads."""
    from services.email.reply_sync import GmailReplySyncService
    try:
        logger.info("▶️ Starting Gmail reply sync job...")
        result = GmailReplySyncService().sync_replies()
        logger.info(f"✅ Reply sync job completed: {result.get('replies_detected', 0)} new replies detected")
        return result
    except Exception as e:
        logger.error(f"❌ Reply sync job failed: {e}", exc_info=True)
        return {"error": str(e), "replies_detected": 0}

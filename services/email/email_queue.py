"""
Async Email Queue System
Provides reliable, asynchronous email sending with retry logic
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import time
from itertools import count

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailPriority(Enum):
    """Email priority levels"""
    LOW = 10        # General notifications
    NORMAL = 5      # Standard pitches
    HIGH = 2        # Urgent follow-ups
    CRITICAL = 0    # System alerts


@dataclass
class EmailTask:
    """Represents an email to be sent"""
    
    outreach_id: str
    to_email: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    priority: EmailPriority = EmailPriority.NORMAL
    attempt_count: int = 0
    max_retries: int = 3
    scheduled_time: float = None  # Unix timestamp
    user_id: str = "default_user"
    tracking_token: Optional[str] = None
    thread_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmailQueue:
    """
    In-memory async email queue with priority support.
    
    In production, replace with Redis or RabbitMQ for persistence.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self.processing: Dict[str, bool] = {}  # Track in-progress tasks
        self._sequence = count()
        
        # Start worker coroutine
        asyncio.create_task(self._process_queue())
    
    async def enqueue(self, task: EmailTask) -> bool:
        """
        Add email task to queue.
        
        Returns True if added, False if queue is full.
        """
        
        if self.queue.qsize() >= self.max_size:
            logger.warning(f"Email queue full, cannot add task {task.outreach_id}")
            return False
        
        # Calculate priority (lower number = higher priority)
        priority_value = task.priority.value
        schedule_time = task.scheduled_time or time.time()
        
        try:
            # Add to priority queue (sorts by priority then time)
            # Sequence number prevents Python from comparing EmailTask objects
            # when priority and timestamp happen to be identical.
            await self.queue.put((priority_value, schedule_time, next(self._sequence), task))
            
            logger.info(f"Email enqueued: {task.outreach_id} (priority: {task.priority.name})")
            return True
            
        except asyncio.QueueFull:
            logger.error(f"Failed to enqueue email: {task.outreach_id}")
            return False
    
    async def _process_queue(self):
        """
        Worker coroutine that continuously processes queued emails.
        
        Runs until application shutdown.
        """
        while True:
            task = None
            try:
                _, scheduled_time, _, task = await self.queue.get()
                
                # Skip if already processing
                if task.outreach_id in self.processing:
                    logger.warning(f"Task {task.outreach_id} already processing, skipping")
                    continue
                
                # Wait until scheduled time (if future-scheduled)
                now = time.time()
                if scheduled_time > now:
                    delay = scheduled_time - now
                    logger.debug(f"Waiting {delay:.1f}s for scheduled email {task.outreach_id}")
                    await asyncio.sleep(delay)
                
                # Mark as processing
                self.processing[task.outreach_id] = True
                
                # Attempt to send
                success = await self._send_with_retry(task)
                
                if success:
                    logger.info(f"✅ Email sent successfully: {task.outreach_id}")
                else:
                    logger.error(f"❌ Email failed after retries: {task.outreach_id}")
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Queue processing error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight loop on errors
            finally:
                if task is not None:
                    self.processing.pop(task.outreach_id, None)
                    self.queue.task_done()
    
    async def _send_with_retry(self, task: EmailTask) -> bool:
        """
        Send email with exponential backoff retry.
        
        Returns True if successful after retries, False otherwise.
        """
        
        for attempt in range(task.max_retries + 1):
            try:
                task.attempt_count = attempt
                
                # Check rate limits before sending
                from middleware.rate_limiter import email_throttler
                
                if not email_throttler.check_email_limit():
                    logger.warning(f"Rate limit reached, retrying {task.outreach_id}")
                    if attempt < task.max_retries:
                        await asyncio.sleep(60)  # Wait 1 minute
                        continue
                    else:
                        return False
                
                # Attempt actual send
                result = await self._send_email(task)
                
                if result:
                    email_throttler.record_send()
                return result
                
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{task.max_retries + 1} failed for {task.outreach_id}: {e}"
                )
                
                # Exponential backoff (1s, 2s, 4s, ...)
                if attempt < task.max_retries:
                    wait_seconds = 2 ** attempt
                    await asyncio.sleep(wait_seconds)
                else:
                    # Final failure after all retries
                    logger.error(f"All retry attempts failed for {task.outreach_id}")
                    return False
        
        return False
    
    async def _send_email(self, task: EmailTask) -> bool:
        """
        Actually send the email using Gmail API or fallback.
        
        Returns True if sent successfully, False otherwise.
        """
        
        # Import sender service (avoid circular imports)
        from services.email.sender import GmailSenderService
        
        try:
            sender = GmailSenderService()
            
            # Queued work is a production delivery path. Missing/revoked OAuth
            # must fail visibly instead of being recorded as a simulated send.
            result = sender.send_pitch(
                to_email=task.to_email,
                subject=task.subject,
                body_text=task.body_text or task.body_html,
                user_id=task.user_id,
                tracking_token=task.tracking_token,
                thread_id=task.thread_id,
                allow_simulation=False,
            )

            return bool(result.get("success"))
            
        except Exception as e:
            logger.error(f"Send email exception for {task.outreach_id}: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        
        return {
            "queue_size": self.queue.qsize(),
            "processing_count": len(self.processing),
            "max_size": self.max_size
        }


# Global email queue instance
email_queue = None  # Lazy initialization when first needed


def get_email_queue():
    """Lazy initializer for email queue"""
    
    global email_queue
    
    if email_queue is None:
        email_queue = EmailQueue()
    
    return email_queue

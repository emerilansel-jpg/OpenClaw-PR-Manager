"""
Rate Limiting Middleware
Implements request throttling to prevent abuse and ensure fair usage
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from functools import wraps
import time

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour", "10/minute"],
    storage_uri="memory://",  # Could use Redis in production
    headers_enabled=True
)


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom error handler for rate limit exceeded errors.
    
    Returns appropriate response with retry information.
    """
    
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down.",
            "retry_after": exc.headers.get("Retry-After"),
            "message": "You've exceeded the rate limit."
        },
        headers={
            "X-RateLimit-Limit": str(exc.value.limit.value),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": int(time.time() + exc.value.reset_time.total_seconds()),
            "Retry-After": str(int(exc.value.reset_time.total_seconds()))
        }
    )


# Register error handler automatically (slowapi handles this)
def register_rate_limit_handler(app):
    """Register rate limit error handler with FastAPI app"""
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please slow down.",
                "retry_after": exc.headers.get("Retry-After"),
                "message": "You've exceeded the rate limit."
            },
            headers={
                "X-RateLimit-Limit": str(exc.value.limit.value),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": int(time.time() + exc.value.reset_time.total_seconds()),
                "Retry-After": str(int(exc.value.reset_time.total_seconds()))
            }
        )


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour", "10/minute"],
    storage_uri="memory://",  # Could use Redis in production
    headers_enabled=True
)


# Decorator function for custom rate limits
def limit_rate(tier: str = "standard"):
    """
    Apply custom rate limits based on tier level.
    
    Tiers:
    - standard: 100/hour, 10/minute (default)
    - premium: 500/hour, 50/minute  
    - enterprise: unlimited
    - strict: 30/hour, 3/minute
    
    Usage: @limit_rate(tier="premium")
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Apply specific rate limit
        if tier == "premium":
            return limiter.limit("500/hour", "50/minute")(wrapper)
        elif tier == "enterprise":
            return limiter.limit(None)(wrapper)  # No limit
        elif tier == "strict":
            return limiter.limit("30/hour", "3/minute")(wrapper)
        else:  # standard
            return limiter.limit("100/hour", "10/minute")(wrapper)
    
    return decorator


class EmailSendThrottler:
    """
    Additional layer of rate limiting specifically for email sending.
    
    Gmail API has its own limits that we need to respect.
    """
    
    def __init__(self, max_per_minute=10, max_per_day=500):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.minutes_requests = {}
        self.daily_count = 0
        self.current_day = None
        
        # Track last day's date
        from datetime import datetime
        self.current_day = datetime.utcnow().date()
    
    def reset_daily_count(self):
        """Reset daily counter at midnight"""
        from datetime import datetime
        today = datetime.utcnow().date()
        if today != self.current_day:
            self.daily_count = 0
            self.current_day = today
            self.minutes_requests.clear()
    
    def check_email_limit(self) -> bool:
        """
        Check if email send is allowed within current limits.
        
        Returns True if can send, False otherwise.
        """
        
        self.reset_daily_count()
        
        # Check daily limit
        if self.daily_count >= self.max_per_day:
            return False
        
        # Get current minute window
        from datetime import datetime
        now = datetime.utcnow()
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        
        # Check per-minute limit
        minute_count = self.minutes_requests.get(minute_key, 0)
        if minute_count >= self.max_per_minute:
            return False
        
        return True
    
    def record_send(self):
        """Record that an email was sent"""
        
        self.reset_daily_count()
        
        from datetime import datetime
        minute_key = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        
        self.minutes_requests[minute_key] = self.minutes_requests.get(minute_key, 0) + 1
        self.daily_count += 1


# Global email throttler instance
email_throttler = EmailSendThrottler()


def initialize_email_services():
    """Initialize email services after event loop starts"""
    
    from services.email import email_queue
    
    # Get lazy-initialized queue
    queue = email_queue.get_email_queue()
    return queue

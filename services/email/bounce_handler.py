"""
Email Bounce Handler
Manages bounced emails and suppression list to prevent repeated failures
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BounceHandler:
    """
    Handles email bounce reports and maintains suppression list.
    
    Features:
    - Records bounce events with reasons
    - Adds email to suppression list to prevent repeated failures
    - Tracks soft/hard bounces
    - Provides statistics on bounce rates
    """
    
    def __init__(self):
        # In-memory suppression list (in production, use database)
        self.suppressed_emails: Dict[str, Dict[str, Any]] = {}
        
        # Bounce reasons classification
        self.bounce_types = {
            "hard": ["domain not found", "address does not exist", "mailbox unavailable"],
            "soft": ["mailbox full", "temporary failure", "rate limited", "server busy"]
        }
    
    def record_bounce(
        self,
        outreach_id: str,
        email: str,
        reason: str,
        is_hard: bool = None
    ) -> Dict[str, Any]:
        """
        Record a bounced email event.
        
        Args:
            outreach_id: Unique identifier of the outreach record
            email: Recipient email address that bounced
            reason: Error message/reason for bounce
            is_hard: Whether this is a hard bounce (auto-detected if not provided)
            
        Returns:
            Dictionary with bounce record details
        """
        
        # Determine bounce type if not provided
        if is_hard is None:
            is_hard = self._is_hard_bounce(reason)
        
        bounce_record = {
            "id": str(uuid.uuid4()),
            "outreach_id": outreach_id,
            "email": email,
            "reason": reason,
            "is_hard_bounce": is_hard,
            "timestamp": datetime.utcnow().isoformat(),
            "added_to_suppression": False
        }
        
        # Add to suppression list
        if is_hard:
            self.suppressed_emails[email.lower()] = bounce_record
            bounce_record["added_to_suppression"] = True
            logger.info(f"📧 Hard bounce - suppressed: {email}")
        else:
            logger.warning(f"📧 Soft bounce - tracking: {email}")
        
        return bounce_record
    
    def is_suppressed(self, email: str) -> bool:
        """
        Check if email address is suppressed (should not send to).
        
        Args:
            email: Email address to check
            
        Returns:
            True if suppressed (hard bounce), False otherwise
        """
        
        return email.lower() in self.suppressed_emails
    
    def remove_from_suppression(self, email: str) -> bool:
        """
        Remove email from suppression list (e.g., after manual verification).
        
        Args:
            email: Email address to restore
            
        Returns:
            True if removed successfully, False if not found
        """
        
        email_lower = email.lower()
        if email_lower in self.suppressed_emails:
            del self.suppressed_emails[email_lower]
            logger.info(f"📧 Removed from suppression: {email}")
            return True
        
        return False
    
    def get_suppressed_count(self) -> int:
        """Get total number of suppressed emails"""
        
        return len(self.suppressed_emails)
    
    def get_bounce_stats(self) -> Dict[str, Any]:
        """
        Get statistics about bounce events.
        
        Returns:
            Dictionary with counts and metrics
        """
        
        hard_count = sum(
            1 for record in self.suppressed_emails.values()
            if record["is_hard_bounce"]
        )
        
        soft_count = len(self.suppressed_emails) - hard_count
        
        return {
            "total_bounces": len(self.suppressed_emails),
            "hard_bounces": hard_count,
            "soft_bounces": soft_count,
            "suppression_list_size": len(self.suppressed_emails)
        }
    
    def _is_hard_bounce(self, reason: str) -> bool:
        """
        Determine if a bounce is hard (permanent) or soft (temporary).
        
        Args:
            reason: Error message from email service
            
        Returns:
            True if hard bounce, False if soft bounce
        """
        
        reason_lower = reason.lower()
        
        # Check against hard bounce patterns
        for pattern in self.bounce_types["hard"]:
            if pattern in reason_lower:
                return True
        
        # Check against soft bounce patterns
        for pattern in self.bounce_types["soft"]:
            if pattern in reason_lower:
                return False
        
        # Default to hard bounce for unknown patterns
        logger.warning(f"⚠️  Unknown bounce type, treating as hard: {reason}")
        return True


# Global bounce handler instance
bounce_handler = BounceHandler()

"""
Email Unsubscribe Management
Handles unsubscribe tokens and suppression requests for email compliance
"""

import jwt
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnsubscribeManager:
    """
    Manages email unsubscribe functionality.
    
    Handles:
    - Token generation for unsubscribe links
    - Token validation
    - Suppression list management
    
    Complies with CAN-SPAM and other email regulations by providing unsubscribe mechanisms.
    """
    
    def __init__(self, secret_key: str = None):
        """
        Initialize unsubscribe manager.
        
        Args:
            secret_key: JWT signing key (from environment or default)
        """
        
        self.secret_key = secret_key or os.getenv(
            "UNSUBSCRIBE_SECRET_KEY", 
            "openclaw-unsubscribe-secret-change-in-production"
        )
    
    def generate_unsubscribe_token(self, outreach_id: str) -> str:
        """
        Generate time-limited unsubscribe token.
        
        Args:
            outreach_id: ID of the outreach record to unsubscribe from
            
        Returns:
            JWT token string valid for 30 days
        """
        
        now = datetime.utcnow()
        expiry = now + timedelta(days=30)
        
        payload = {
            "outreach_id": outreach_id,
            "exp": expiry,
            "iat": now,
            "action": "unsubscribe"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def validate_unsubscribe_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate unsubscribe token and extract details.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Payload dict if valid, None if invalid/expired
        """
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Validate required fields
            if payload.get("action") != "unsubscribe":
                logger.error(f"Invalid action type in token: {payload.get('action')}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired unsubscribe token received")
            return None
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid unsubscribe token: {e}")
            return None
    
    def unsubscribe_from_campaign(
        self, 
        outreach_id: str,
        email: str
    ) -> bool:
        """
        Process unsubscribe request for outreach/campaign.
        
        In production:
        1. Mark outreach as unsubscribed
        2. Add email to global suppression list
        3. Update journalist profile preferences
        
        Args:
            outreach_id: Campaign/outreach to unsubscribe from
            email: Email address that unsubscribed
            
        Returns:
            True if processed successfully
        """
        
        try:
            # This would normally interact with database repositories
            # For now, log the action
            
            logger.info(f"📧 User unsubscribed from campaign {outreach_id}")
            logger.info(f"   Email: {email}")
            
            # In production, you would:
            # 1. Update outreach status
            # await outreach_repo.update_status(outreach_id, "unsubscribed")
            
            # 2. Add to suppression list
            # from services.email.bounce_handler import bounce_handler
            # bounce_handler.suppressed_emails[email.lower()] = {
            #     "reason": "user_unsubscribed",
            #     "timestamp": datetime.utcnow().isoformat(),
            #     "is_hard_bounce": False  # Not a hard bounce, just opt-out
            # }
            
            # 3. Update journalist preferences
            # await update_journalist_preferences(email, {"accept_marketing": False})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process unsubscribe: {e}")
            return False
    
    def get_unsubscribe_link(self, outreach_id: str) -> str:
        """
        Get full unsubscribe URL.
        
        Args:
            outreach_id: ID of the outreach
            
        Returns:
            Full unsubscribe link (would include domain in production)
        """
        
        token = self.generate_unsubscribe_token(outreach_id)
        
        # Build complete URL (domain would come from settings)
        base_url = "http://localhost:8501/links"  # Placeholder
        # Production: use actual tracking domain
        # base_url = settings.TRACKING_BASE_URL.replace("/api/v1/outreach/track", "")
        
        return f"{base_url}/unsubscribe?token={token}"


# Global unsubscribe manager instance
unsubscribe_manager = UnsubscribeManager()

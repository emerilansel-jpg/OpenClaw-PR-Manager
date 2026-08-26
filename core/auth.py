"""
Core Authentication Utilities
Handles JWT token generation/validation, password hashing, and auth middleware
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import jwt
import bcrypt


class AuthManager:
    """Manages JWT tokens and password operations."""
    
    # Token configuration
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    
    @classmethod
    def create_access_token(
        cls, 
        user_id: str, 
        email: str,
        expires_delta: timedelta = None
    ) -> str:
        """Create JWT access token for authenticated user."""
        
        if expires_delta is None:
            expires_delta = timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        now = datetime.utcnow()
        expire = now + expires_delta
        
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": now,
            "type": "access"
        }
        
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        """Create JWT refresh token for long-term sessions."""
        
        now = datetime.utcnow()
        expire = now + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh"
        }
        
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload if valid."""
        
        try:
            payload = jwt.decode(
                token, 
                cls.SECRET_KEY, 
                algorithms=[cls.ALGORITHM]
            )
            
            # Validate token type
            if payload.get("type") != expected_type:
                raise ValueError(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
            
            # Check expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                raise ValueError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using bcrypt."""
        
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed.encode('utf-8')
        )
    
    @classmethod
    def get_token_payload(cls, token: str) -> Dict[str, Any]:
        """Extract token payload without raising errors (for testing)."""
        
        try:
            return jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
        except Exception:
            return {}
    
    @classmethod
    def require_organization_access(
        cls, 
        user_id: str, 
        target_org_id: str
    ) -> bool:
        """
        Verify user belongs to target organization.
        This should be called by repositories, not in this layer.
        Returns True if user has access.
        """
        
        # Note: Actual check happens in repository layer via database query
        # This is a placeholder for documentation
        return True  # Will be validated by DB RLS policies

# Global auth instance
auth_manager = AuthManager()


def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """Helper function to extract current user from JWT token."""
    
    payload = auth_manager.verify_token(token)
    return {
        "user_id": payload["sub"],
        "email": payload["email"]
    }


def validate_jwt_credentials(username: str, password: str) -> Dict[str, str]:
    """
    Validate username/password combination and return tokens if successful.
    This would typically be called after checking credentials in database.
    """
    
    # In production, this would verify against profiles table
    # For now, returns mock tokens (will be replaced with actual logic)
    
    if not username or not password:
        raise ValueError("Username and password required")
    
    # TODO: Implement actual user lookup and password verification
    
    user_id = f"user_{username}"  # Placeholder
    return {
        "access_token": auth_manager.create_access_token(user_id, username),
        "refresh_token": auth_manager.create_refresh_token(user_id)
    }

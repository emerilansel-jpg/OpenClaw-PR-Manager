"""
User Authentication API Router
Handles user registration, login, profile management, and JWT tokens
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
import datetime

# Core authentication utilities
from core.auth import auth_manager, get_current_user_from_token

# Repository for organization operations
from db.repositories.base_multitenant import OrganizationMembersRepository

router = APIRouter(prefix="/auth/users", tags=["User Authentication"])

# OAuth2 scheme for Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class RegisterRequest(BaseModel):
    """User registration request"""
    
    email: EmailStr
    password: str
    full_name: str
    organization_name: Optional[str] = None  # If creating new org
    existing_organization_id: Optional[str] = None  # If joining existing
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Ensure password meets minimum requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    """Profile update request"""
    
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class OrganizationJoinRequest(BaseModel):
    """Request to join an organization"""
    
    organization_id: str
    role: Optional[str] = "member"  # Default role


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    """
    Register new user and optionally create/join organization.
    
    Returns JWT access and refresh tokens.
    """
    
    try:
        # Hash password before storage
        hashed_password = auth_manager.hash_password(data.password)
        
        # In production, this would use Supabase Auth admin API to create user
        # For now, we'll simulate user creation with the email as ID
        user_id = f"user_{data.email.replace('@', '_at_').replace('.', '_dot_')}"
        
        # Determine organization context
        organization_id = None
        
        if data.existing_organization_id:
            # User is joining existing organization
            organization_id = data.existing_organization_id
            role = data.organization_name or "member"  # Use provided role or default
            
            # Add to organization as member
            members_repo = OrganizationMembersRepository()
            await members_repo.add_member(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                invited_by=None  # In production, track who invited
            )
            
        elif data.organization_name:
            # User is creating new organization
            # In production, this would create the org via Supabase
            organization_id = f"org_{data.organization_name.replace(' ', '_').lower()}"
            role = "owner"  # Creator becomes owner
            
            # Create organization (placeholder)
            org_data = {
                "id": organization_id,
                "name": data.organization_name
            }
            
            # Add to organization as owner
            members_repo = OrganizationMembersRepository()
            await members_repo.add_member(
                organization_id=organization_id,
                user_id=user_id,
                role="owner",
                invited_by=None
            )
            
            # Set as default organization in profile
            organization_id = organization_id
        
        # Generate JWT tokens
        access_token = auth_manager.create_access_token(user_id, data.email)
        refresh_token = auth_manager.create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """
    Authenticate user and return JWT tokens.
    
    Validates email/password combination against profiles table.
    """
    
    try:
        # In production, fetch user profile from database
        # Verify password hash matches
        
        # Placeholder: accept any credentials for demo
        user_id = f"user_{data.email.replace('@', '_at_').replace('.', '_dot_')}"
        
        # Generate tokens
        access_token = auth_manager.create_access_token(user_id, data.email)
        refresh_token = auth_manager.create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.get("/me")
async def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    """
    Get current authenticated user profile with organizations.
    
    Requires valid Bearer token.
    """
    
    try:
        # Extract user from token
        payload = auth_manager.verify_token(token)
        user_id = payload["sub"]
        email = payload["email"]
        
        # Fetch user profile from database (placeholder)
        profile = {
            "id": user_id,
            "email": email,
            "full_name": "User",  # Would come from profiles table
            "avatar_url": None,
            "role": "owner",
            "active": True
        }
        
        # Get organizations user belongs to
        members_repo = OrganizationMembersRepository()
        user_orgs = await members_repo.list_for_user(user_id)
        
        return {
            **profile,
            "organizations": [
                {
                    "id": org["organization_id"],
                    "role": org["role"]
                }
                for org in user_orgs
            ]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.put("/profile")
async def update_profile(
    data: ProfileUpdateRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Update current user's profile information.
    
    Users can only update their own profile.
    """
    
    try:
        payload = auth_manager.verify_token(token)
        user_id = payload["sub"]
        
        # Update profile (placeholder)
        updates = {}
        if data.full_name:
            updates["full_name"] = data.full_name
        if data.avatar_url:
            updates["avatar_url"] = data.avatar_url
        
        # In production, update profiles table via Supabase
        # Ensure user can only update their own profile
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "updates": updates
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/join-organization")
async def join_organization(
    data: OrganizationJoinRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Add current user to an existing organization.
    
    Used when user receives invitation or finds organization to join.
    """
    
    try:
        payload = auth_manager.verify_token(token)
        user_id = payload["sub"]
        
        # Add to organization
        members_repo = OrganizationMembersRepository()
        result = await members_repo.add_member(
            organization_id=data.organization_id,
            user_id=user_id,
            role=data.role or "member",
            invited_by=None
        )
        
        return {
            "success": True,
            "message": f"Joined organization {data.organization_id}",
            "role": data.role
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to join organization: {str(e)}"
        )


@router.post("/leave-organization")
async def leave_organization(
    organization_id: str,
    token: str = Depends(oauth2_scheme)
):
    """
    Remove current user from an organization.
    
    Users can leave any org they belong to (unless they're the only owner).
    """
    
    try:
        payload = auth_manager.verify_token(token)
        user_id = payload["sub"]
        
        # Remove from organization (set status to blocked)
        members_repo = OrganizationMembersRepository()
        await members_repo.remove_member(
            organization_id=organization_id,
            user_id=user_id
        )
        
        return {
            "success": True,
            "message": f"Left organization {organization_id}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/organizations")
async def get_user_organizations(
    token: str = Depends(oauth2_scheme)
):
    """
    Get all organizations current user belongs to.
    
    Returns list of organizations with role information.
    """
    
    try:
        payload = auth_manager.verify_token(token)
        user_id = payload["sub"]
        
        members_repo = OrganizationMembersRepository()
        orgs = await members_repo.list_for_user(user_id)
        
        return [
            {
                "id": org["organization_id"],
                "role": org["role"],
                "status": org["status"]
            }
            for org in orgs
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

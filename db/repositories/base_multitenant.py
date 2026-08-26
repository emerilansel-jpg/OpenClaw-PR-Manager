"""
Multi-Tenant Base Repository Pattern
Provides organization-aware CRUD operations with authorization
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from db.supabase_client import SupabaseClientProvider
    from core.auth import auth_manager
except ImportError:
    # Fallback for direct execution
    SupabaseClientProvider = None


class MultiTenantBaseRepository:
    """
    Abstract base class for all multi-tenant repositories.
    
    Provides:
    - Organization ID injection on create operations
    - Organization ID filtering on query operations
    - Authorization validation hooks
    - Audit logging support
    """
    
    def __init__(self, table_name: str):
        """
        Initialize repository.
        
        Args:
            table_name: Name of database table managed by this repository
        """
        
        self.table_name = table_name
        self.client = SupabaseClientProvider.get_client() if SupabaseClientProvider else None
        self.organization_id: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def set_context(self, organization_id: str, user_id: str):
        """
        Set current request context (organization + user).
        
        This should be called before any repository operation.
        """
        
        self.organization_id = organization_id
        self.user_id = user_id
    
    def _inject_organization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject organization_id into data on create/update.
        
        Args:
            data: Dictionary of fields to insert/update
            
        Returns:
            Data dictionary with organization_id added
        """
        
        if not self.organization_id:
            raise ValueError("Organization context not set")
        
        data["organization_id"] = self.organization_id
        
        return data
    
    def _filter_by_organization(self, query) -> object:
        """
        Apply organization filter to Supabase query.
        
        Args:
            query: Supabase client query object
            
        Returns:
            Query object filtered by organization_id
        """
        
        if not self.organization_id:
            return query
        
        return query.eq("organization_id", self.organization_id)
    
    def validate_access(self, target_record: Dict[str, Any]):
        """
        Validate user has access to target record's organization.
        
        Args:
            target_record: Record data containing organization_id
            
        Raises:
            HTTPException 403 if no access
        """
        
        target_org_id = target_record.get("organization_id")
        
        if not target_org_id or not self.organization_id:
            raise Exception("Authorization failed: Missing organization data")
        
        if target_org_id != self.organization_id:
            raise Exception(
                f"Access denied: User belongs to org {self.organization_id}, "
                f"but record belongs to {target_org_id}"
            )
    
    def audit_log_action(
        self, 
        action: str, 
        resource_type: str, 
        resource_id: Optional[str],
        changes: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log action to audit_logs table.
        
        Args:
            action: Type of action (create, update, delete, etc.)
            resource_type: Type of resource (journalist, campaign, etc.)
            resource_id: ID of affected resource
            changes: Before/after changes (optional)
            success: Whether action succeeded
            error_message: Error details if failed
        """
        
        if not self.client or not self.user_id or not self.organization_id:
            # Skip logging if context not available
            return
        
        try:
            audit_data = {
                "organization_id": self.organization_id,
                "user_id": self.user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "changes": changes,
                "success": success,
                "error_message": error_message
            }
            
            # In production, insert to audit_logs table
            # For now, log to console
            print(f"[AUDIT] {action}: {resource_type} {resource_id}")
            
        except Exception as e:
            # Don't fail operation if audit logging fails
            print(f"[AUDIT ERROR] Failed to log action: {e}")


class OrganizationMembersRepository(MultiTenantBaseRepository):
    """
    Repository for managing organization membership.
    Handles joining/leaving organizations and role management.
    """
    
    def __init__(self):
        super().__init__("organization_members")
    
    async def add_member(
        self, 
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add user to organization."""
        
        self.set_context(organization_id, user_id)
        
        member_data = {
            "organization_id": organization_id,
            "user_id": user_id,
            "role": role,
            "invited_by": invited_by,
            "status": "active",
            "accepted_at": datetime.utcnow().isoformat()
        }
        
        result = self.client.table("organization_members").insert(member_data).execute()
        return result.data[0]
    
    async def remove_member(self, organization_id: str, user_id: str) -> None:
        """Remove user from organization (soft delete via status)."""
        
        self.set_context(organization_id, user_id)
        
        await self.client.table("organization_members").update(
            {"status": "blocked", "updated_at": datetime.utcnow().isoformat()}
        ).eq("organization_id", organization_id).eq("user_id", user_id).execute()
    
    async def list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all organizations user belongs to."""
        
        result = await self.client.table("organization_members").select("*").eq(
            "user_id", user_id
        ).eq("status", "active").execute()
        
        return result.data


class APIKeysRepository(MultiTenantBaseRepository):
    """Repository for managing API keys."""
    
    def __init__(self):
        super().__init__("api_keys")
    
    async def create_key(
        self, 
        organization_id: str,
        name: str,
        key_hash: str,
        key_prefix: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new API key."""
        
        self.set_context(organization_id, None)  # API keys not user-scoped
        
        key_data = {
            "organization_id": organization_id,
            "name": name,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "scopes": scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_by": created_by
        }
        
        result = await self.client.table("api_keys").insert(key_data).execute()
        return result.data[0]
    
    async def revoke_key(self, key_id: str) -> None:
        """Revoke API key."""
        
        await self.client.table("api_keys").update({
            "revoked_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", key_id).execute()
    
    async def get_active_keys(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all active (not revoked) API keys for organization."""
        
        result = await self.client.table("api_keys").select("*").eq(
            "organization_id", organization_id
        ).eq("revoked_at", None).execute()
        
        return result.data

"""Supabase client initialization with graceful fallback for local testing."""
import logging
from typing import Optional, Any, Dict, List
from supabase import create_client, Client
from config.settings import get_settings

logger = logging.getLogger(__name__)


class SupabaseClientProvider:
    """Manages Supabase client lifecycle."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Client] = None

    def get_client(self) -> Optional[Client]:
        """Returns initialized Supabase Client if configured, else None."""
        if not self.settings.is_supabase_configured:
            logger.info("Supabase is not configured or using placeholder credentials. Running in local/mock mode.")
            return None

        if self._client is None:
            try:
                # Use service role key if available for administrative capabilities
                key = self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY
                self._client = create_client(self.settings.SUPABASE_URL, key)
                logger.info("Successfully connected to Supabase at %s", self.settings.SUPABASE_URL)
            except Exception as e:
                logger.error("Failed to initialize Supabase client: %s", e)
                self._client = None

        return self._client


client_provider = SupabaseClientProvider()


def get_supabase_client() -> Optional[Client]:
    """Helper function to get supabase client."""
    return client_provider.get_client()

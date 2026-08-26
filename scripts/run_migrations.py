"""Supabase Migration Runner Helper."""
import os
import glob
from config.settings import get_settings

def print_migration_instructions():
    settings = get_settings()
    print("=" * 70)
    print("OpenClaw PR Manager - Supabase SQL Migrations")
    print("=" * 70)
    
    migration_files = sorted(glob.glob("db/migrations/*.sql"))
    if not migration_files:
        print("No migration files found in db/migrations/")
        return

    print(f"Found {len(migration_files)} migration files:\n")
    for f in migration_files:
        print(f"  -> {f}")
        
    print("\nHow to apply migrations to Supabase:")
    print("1. Open your Supabase Dashboard: https://supabase.com/dashboard")
    print("2. Navigate to your project -> 'SQL Editor'")
    print("3. Paste the contents of each file in order (001 -> 002 -> 003) and click 'Run'.")
    print("=" * 70)

if __name__ == "__main__":
    print_migration_instructions()

"""
Supabase Configuration Helper
Safely guides user through .env setup and migration execution
"""

import os
import sys
from pathlib import Path
import subprocess

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def read_env_file():
    """Read current .env file if it exists."""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            return f.read()
    return ""

def update_env_file(supabase_url, supabase_key, service_role_key=None):
    """Update .env file with Supabase credentials."""
    
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    # Start with existing .env content
    env_content = ""
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.read()
    
    # Add/Update Supabase section
    lines = []
    
    # Check if SUPABASE_URL already exists
    has_supabase = "SUPABASE_URL" in env_content
    has_key = "SUPABASE_KEY" in env_content
    has_service_role = "SUPABASE_SERVICE_ROLE_KEY" in env_content
    
    if not has_supabase:
        # Add Supabase section
        lines.append("\n# ------------------------------------------------------------------------------")
        lines.append("# Supabase Configuration")
        lines.append("# ------------------------------------------------------------------------------")
        lines.append(f"SUPABASE_URL={supabase_url}")
        lines.append(f"SUPABASE_KEY={supabase_key}")
        if service_role_key:
            lines.append(f"SUPABASE_SERVICE_ROLE_KEY={service_role_key}")
        lines.append("\n")
    
    # Write updated content
    updated_content = env_content + "\n".join(lines)
    
    with open(env_path, 'w') as f:
        f.write(updated_content)
    
    print(f"✅ .env file updated successfully")
    print(f"   SUPABASE_URL: {'*' * 20}")
    print(f"   SUPABASE_KEY: {'*' * 20}")
    if service_role_key:
        print(f"   SERVICE_ROLE_KEY: {'*' * 20}")

def show_migration_instructions():
    """Display migration instructions."""
    
    print_section("🗄️  Database Migrations Required")
    
    print("""
Next steps to complete Supabase setup:

1. Open Supabase Dashboard → SQL Editor
2. Run migrations in ORDER:

   📋 db/migrations/001_initial_schema.sql
      → Creates tables, indexes, enables pgvector & uuid-ossp
   
   📋 db/migrations/002_rls_policies.sql  
      → Adds Row Level Security policies
   
   📋 db/migrations/003_functions.sql
      → Adds triggers and vector search functions
   
   📋 db/migrations/004_gmail_account_key.sql
      → Adds account_key for Gmail token sharing

3. Verify connection with:
   python -c "from config.settings import get_settings; s=get_settings(); print('supabase_configured:', s.is_supabase_configured)"
   
   Should output: supabase_configured: True

⚠️  IMPORTANT SECURITY NOTES:
   - The current RLS policies are permissive (development mode)
   - Replace with strict policies before production use
   - Never commit .env to version control
   - Service role key must remain server-only

📚 For detailed migration guide, see: docs/integrations.md#supabase
""")

def verify_configuration():
    """Verify Supabase is configured correctly."""
    
    print_section("🔍 Verifying Configuration")
    
    try:
        result = subprocess.run(
            ["python", "-c", "from config.settings import get_settings; s=get_settings(); print('supabase_configured:', s.is_supabase_configured)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if "True" in output:
            print("✅ Supabase configured successfully!")
            print(f"   Status: {output}")
        elif "False" in output:
            print("⚠️  Supabase configuration found but may have issues")
            print(f"   Status: {output}")
            print("\n   Please check:")
            print("   - SUPABASE_URL format (should be https://<project>.supabase.co)")
            print("   - SUPABASE_KEY is valid anon/public key")
        else:
            print("❌ Could not verify configuration")
            if error:
                print(f"   Error: {error}")
            print("\n   Make sure:")
            print("   1. .env file exists in project root")
            print("   2. Python dependencies are installed: pip install -r requirements.txt")
            
    except subprocess.TimeoutExpired:
        print("⏱️  Verification timed out")
    except FileNotFoundError:
        print("❌ Python not found in PATH")
    except Exception as e:
        print(f"❌ Error during verification: {e}")

def main():
    """Main setup workflow."""
    
    print_section("🚀 Supabase Setup Assistant")
    print("Welcome to OpenClaw PR Manager!\n")
    
    # Read existing .env
    current_env = read_env_file()
    
    if "SUPABASE_URL" in current_env:
        print("ℹ️  Found existing Supabase configuration in .env")
        response = input("Do you want to update it? (y/N): ").strip().lower()
        if response != 'y':
            print("Exiting without changes.")
            return
    
    # Collect credentials
    print("\nPlease enter your Supabase credentials:\n")
    
    supabase_url = input("Project URL (https://<project>.supabase.co): ").strip()
    if not supabase_url:
        print("❌ Project URL is required")
        return
    
    supabase_key = input("Publishable Key (anon/public): ").strip()
    if not supabase_key:
        print("❌ Publishable Key is required")
        return
    
    service_role_key = input("Service Role Key (optional, press Enter to skip): ").strip() or None
    
    # Confirm before writing
    print(f"\nYou entered:")
    print(f"  URL: {supabase_url[:30]}...")
    print(f"  Key: {supabase_key[:30]}...")
    if service_role_key:
        print(f"  Service: {service_role_key[:30]}...")
    
    confirm = input("\nUpdate .env with these credentials? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return
    
    # Update .env
    try:
        update_env_file(supabase_url, supabase_key, service_role_key)
    except Exception as e:
        print(f"❌ Failed to update .env: {e}")
        return
    
    # Show next steps
    show_migration_instructions()
    
    # Ask to verify
    verify = input("\nVerify configuration now? (y/N): ").strip().lower()
    if verify == 'y':
        verify_configuration()

if __name__ == "__main__":
    main()

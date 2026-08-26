"""
Production Setup Verification Script
Verifies all critical components are properly configured and working
"""

import sys
from pathlib import Path
import asyncio
import time
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(text):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_check(label, success, message=""):
    """Print checkmark or X for test result"""
    status = "✅" if success else "❌"
    print(f"{status} {label}")
    if message and not success:
        print(f"   ⚠️  {message}")


async def verify_python_imports():
    """Verify all critical modules can be imported"""
    
    print_header("PYTHON IMPORT VERIFICATION")
    
    checks = [
        ("core.auth", "Auth utilities"),
        ("api.lifecyle", "Lifecycle management"),
        ("middleware.rate_limiter", "Rate limiter"),
        ("services.email.email_queue", "Email queue"),
        ("services.email.smtp_fallback", "SMTP fallback"),
        ("services.email.bounce_handler", "Bounce handler"),
        ("services.email.unsubscribe", "Unsubscribe manager"),
    ]
    
    results = []
    
    for module_name, description in checks:
        try:
            __import__(module_name)
            print_check(description, True)
            results.append(True)
        except ImportError as e:
            print_check(description, False, f"Import error: {e}")
            results.append(False)
    
    return all(results)


def verify_database_migration_exists():
    """Verify migration 005 SQL file exists"""
    
    print_header("DATABASE MIGRATION CHECK")
    
    migration_path = Path("db/migrations/005_auth_system.sql")
    
    if migration_path.exists():
        print_check("Migration 005 file", True, "Ready to run in Supabase")
        return True
    else:
        print_check("Migration 005 file", False, "File not found")
        return False


def verify_env_configured():
    """Verify .env has required credentials"""
    
    print_header("ENVIRONMENT CONFIGURATION")
    
    # Check if .env exists
    env_path = Path(".env")
    if env_path.exists():
        print_check(".env file exists", True)
        
        with open(env_path, 'r') as f:
            content = f.read()
        
        checks = [
            ("SUPABASE_URL=" in content, "Supabase URL"),
            ("SUPABASE_KEY=" in content, "Supabase Key"),
            ("JWT_SECRET_KEY=" in content, "JWT Secret Key (recommended)"),
        ]
        
        for check, name in checks:
            print_check(name, check, "" if check else "Required but not set")
        
        return all(check for check, _ in checks)
    else:
        print_check(".env file", False, "Not found - copy from .env.example")
        return False


def verify_api_routing():
    """Verify new routes are registered in FastAPI app"""
    
    print_header("FASTAPI ROUTE REGISTRATION")
    
    try:
        from api.main import app
        
        routes = [route.path for route in app.routes]
        
        expected_routes = [
            "/api/v1/auth/users/register",
            "/api/v1/auth/users/login",
            "/api/v1/auth/users/me",
        ]
        
        for route in expected_routes:
            exists = any(route in r for r in routes)
            print_check(f"Route: {route}", exists)
        
        return all(any(r in ex for r in routes) for ex in expected_routes)
        
    except Exception as e:
        print_check("API routing verification", False, str(e))
        return False


def verify_scheduler_import():
    """Verify APScheduler can be imported"""
    
    print_header("BACKGROUND SCHEDULER CHECK")
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        print_check("APScheduler installed", True)
        
        # Test creating a scheduler instance
        scheduler = BackgroundScheduler()
        scheduler.shutdown()
        print_check("Scheduler instantiation", True)
        
        return True
    except ImportError:
        print_check("APScheduler installed", False, "Install: pip install apscheduler")
        return False
    except Exception as e:
        print_check("Scheduler test", False, str(e))
        return False


def verify_components_exist():
    """Verify all new Python files exist"""
    
    print_header("FILE EXISTENCE CHECK")
    
    files = [
        "core/auth.py",
        "api/lifecyle.py",
        "middleware/rate_limiter.py",
        "services/email/email_queue.py",
        "services/email/smtp_fallback.py",
        "services/email/bounce_handler.py",
        "services/email/unsubscribe.py",
        "db/repositories/base_multitenant.py",
        "api/routers/auth_users.py",
    ]
    
    all_exist = True
    
    for file_path in files:
        exists = Path(file_path).exists()
        print_check(file_path, exists)
        all_exist = all_exist and exists
    
    return all_exist


async def main():
    """Run all verification checks"""
    
    print("\n" + "="*60)
    print("🔍 OPENCLAW PRODUCTION SETUP VERIFICATION")
    print("="*60)
    
    results = []
    
    # Run checks
    results.append(await verify_python_imports())
    results.append(verify_database_migration_exists())
    results.append(verify_env_configured())
    results.append(verify_api_routing())
    results.append(verify_scheduler_import())
    results.append(verify_components_exist())
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print("\nYour OpenClaw PR Manager is ready for production deployment.")
        print("\nNext steps:")
        print("1. Run migration 005 in Supabase dashboard")
        print("2. Configure JWT_SECRET_KEY in .env")
        print("3. Start API server: python -m uvicorn api.main:app --reload")
        print("4. Verify background scheduler starts")
        exit_code = 0
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\nSome issues found above. Please fix before deployment.")
        exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    exit_code = loop.run_until_complete(main())
    loop.close()
    
    sys.exit(exit_code)

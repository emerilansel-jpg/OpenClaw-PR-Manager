"""Email validator and domain verification service."""
import re
import dns.resolver
from typing import Dict, Any, Tuple

# Common disposable email provider domains to reject
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "throwawaymail.com", "trashmail.com"
}

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


class EmailValidator:
    """Validates journalist email format and MX records."""

    @classmethod
    def is_valid_syntax(cls, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        email = email.strip()
        if len(email) > 254:
            return False
        return bool(EMAIL_REGEX.match(email))

    @classmethod
    def check_mx_record(cls, domain: str) -> bool:
        """Check if domain has valid MX (Mail Exchange) DNS records."""
        try:
            records = dns.resolver.resolve(domain, 'MX', lifetime=3.0)
            return len(records) > 0
        except Exception:
            return False

    @classmethod
    def validate(cls, email: str, check_dns: bool = False) -> Dict[str, Any]:
        """Performs full validation check."""
        if not email:
            return {"valid": False, "reason": "Empty email"}

        email_clean = email.strip().lower()
        if not cls.is_valid_syntax(email_clean):
            return {"valid": False, "reason": "Invalid email syntax"}

        domain = email_clean.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            return {"valid": False, "reason": "Disposable email provider"}

        mx_valid = True
        if check_dns:
            mx_valid = cls.check_mx_record(domain)

        return {
            "valid": mx_valid,
            "email": email_clean,
            "domain": domain,
            "mx_checked": check_dns,
            "reason": "OK" if mx_valid else "Domain has no valid MX records"
        }

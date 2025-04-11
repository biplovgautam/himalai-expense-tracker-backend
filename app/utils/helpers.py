import random
import string
from datetime import datetime, timedelta

def generate_verification_code(length: int = 6) -> str:
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))

def get_code_expiry(minutes: int = 30) -> datetime:
    """Get expiry time for verification code"""
    return datetime.utcnow() + timedelta(minutes=minutes)

def parse_full_name(full_name: str) -> tuple:
    """Parse full name into first and last name"""
    parts = full_name.strip().split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name
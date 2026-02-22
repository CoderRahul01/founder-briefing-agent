import os, re
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# We use a master key from environment variables.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY must be set in environment for secure token storage.")

fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    if not token:
        return None
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return None
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception:
        return None

def sanitize_external_content(content: str) -> str:
    """
    Sanitizes content from external websites (competitors) to mitigate
    indirect prompt injection. Removes dangerous patterns and truncates.
    """
    if not content or not isinstance(content, str):
        return ""

    # 1. Remove obvious injection attempts like "Ignore all previous instructions"
    # This is a basic filter, but adds a layer of defense.
    dangerous_patterns = [
        r"(?i)ignore\s+all\s+previous\s+instructions",
        r"(?i)system\s+prompt\s+is",
        r"(?i)you\s+are\s+now\s+a",
        r"(?i)new\s+role\s+is"
    ]
    
    sanitized = content
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "[FILTERED_INJECTION]", sanitized)

    # 2. Strip HTML tags (basic sanitization)
    sanitized = re.sub(r'<[^>]*?>', '', sanitized)

    # 3. Limit length to prevent context window bloating/overflow attacks
    return sanitized[:2000]

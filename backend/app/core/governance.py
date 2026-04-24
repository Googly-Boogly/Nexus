import re
import time
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.core.security import accessible_levels, clearance_level

PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b(?:\d[ -]?){13,16}\b", "credit_card"),
    (r"\bAKIA[0-9A-Z]{16}\b", "aws_access_key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key"),
    (r"(?i)password\s*[=:]\s*\S+", "password_literal"),
]

FORBIDDEN_COMMANDS = [
    r"rm\s+-rf",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM\s+\w+\s*;?\s*$",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"os\.system\s*\(",
    r"subprocess\.(run|call|Popen)",
    r"__import__\s*\(",
    r"format\s+[Cc]:\s*\/",
]


class PIIRedactionResult:
    def __init__(self, text: str, redacted: bool, types_found: list[str]):
        self.text = text
        self.redacted = redacted
        self.types_found = types_found


class GovernanceLayer:

    def redact_pii(self, text: str) -> PIIRedactionResult:
        redacted = text
        types_found = []
        for pattern, label in PII_PATTERNS:
            if re.search(pattern, redacted):
                types_found.append(label)
                redacted = re.sub(pattern, f"[{label.upper()}_REDACTED]", redacted)
        return PIIRedactionResult(redacted, bool(types_found), types_found)

    def check_forbidden(self, text: str) -> list[str]:
        found = []
        for pattern in FORBIDDEN_COMMANDS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern[:30])
        return found

    def check_length(self, text: str) -> bool:
        return len(text) <= settings.MAX_INPUT_LENGTH

    def check_clearance(self, user_clearance: str, required_clearance: str) -> bool:
        return clearance_level(user_clearance) >= clearance_level(required_clearance)


_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def check_rate_limit(user_id: str) -> bool:
    """Returns True if within limit, raises RateLimitExceeded if not."""
    try:
        r = get_redis()
        key = f"rate:{user_id}"
        now = time.time()
        window = 60
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        count = results[2]
        if count > settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            raise RateLimitExceeded(f"Rate limit exceeded: {count} requests in last minute")
        return True
    except RateLimitExceeded:
        raise
    except Exception:
        return True


class RateLimitExceeded(Exception):
    pass

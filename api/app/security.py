import uuid
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings


def create_token(user_id: int, username: str) -> tuple[str, str, int]:
    """Returns (token, jti, exp_epoch)."""
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(seconds=settings.jwt_ttl_seconds)).timestamp())
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_alg)
    return token, jti, exp


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),   # unwrap SecretStr
        algorithms=[settings.jwt_alg],
    )
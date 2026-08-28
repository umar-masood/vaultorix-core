from schemas.auth.logout import LogoutRequest
from schemas.common import Response
from .token import (
    revoke_token, 
    validate_token
)
from utils.logger import log
from exceptions.errors import (
    UNAUTHORIZED, 
    DB_ERROR
)
from db import database
from repositories.user import UPDATE_LAST_USED_AT_BY_ID
from datetime import datetime, timezone

async def init_logout(data : LogoutRequest) -> dict:
    # Validating refresh token
    payload = await validate_token(token_type = "Refresh", token = data.refresh_token)
    if payload is None:
        return UNAUTHORIZED

    # Extracting user id from token payload
    user_id = int(payload["sub"])
    
    # Updating the `last_used_at` field inside database
    try:
        async with database.dbPool.acquire() as conn:
            await conn.execute(
                UPDATE_LAST_USED_AT_BY_ID,
                datetime.now(timezone.utc),
                user_id
            )
            
    except Exception as ex:
        # PostgreSQL database error
        log.error(f'PostgreSQL database error: {ex}')
        return DB_ERROR

    # Revoking refresh token
    await revoke_token(user_id, "Refresh")

    log.info(f"Successful revoked refresh token for {user_id}")

    return Response (
        status_code   = 200,
        message       = "Logged out."
    )

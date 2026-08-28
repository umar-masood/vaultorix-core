from .token import (
    generate_token, 
    validate_token
)
from schemas.auth.refresh import (
    RefreshTokenRequest, 
    RefreshTokenResponse
)
from utils.logger import log
from exceptions.errors import (
    MAX_ATTEMPTS_REACHED, 
    UNAUTHORIZED
)
from db.redis import (
    has_exceeded_limit,
    increment_limit
)
from datetime import datetime, timezone
import os
    
async def init_refresh(data : RefreshTokenRequest) -> dict:
    """
    This function takes refresh token from client, validates and then generates a new access token and return it back to the client.
    """
    
    # Validating refresh token
    payload = await validate_token(token = data.refresh_token, token_type = "Refresh")
    if payload is None: 
        log.warning("Invalid refresh token is provided for refreshing Access token.")
        return UNAUTHORIZED
    
    # Extracting user_id from refresh token payload
    user_id = payload["sub"]

    # Checking max limit
    if await has_exceeded_limit(user_id = user_id, key_name = "RefreshTokenAttempts", attempts_limit = 3):
        log.warning(f"Maximum limit of refreshing access token is reacher for {user_id}.")
        return MAX_ATTEMPTS_REACHED

    # Increment in max limit
    await increment_limit(user_id = user_id, key_name = "RefreshTokenAttempts", ex = 5 * 60) # 5 Minutes
    
    # Generating a new access token
    access_token = generate_token(user_id = user_id, token_type = "Access")

    log.info(f"Successfully generated a new access token for {user_id}.")
    
    return RefreshTokenResponse (
        access_token                = access_token,
        access_token_expires_in     = int(os.getenv("ACCESS_TOKEN_EXPIRY")),
        issued_at                   = int(datetime.now(timezone.utc).timestamp())
    )

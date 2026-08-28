from db import redis, database
from utils.utils import *
from exceptions.errors import *
from fastapi import Request
from repositories.user import (
    SELECT_USER_DETAILS_BY_USERNAME,
    UPDATE_LAST_LOGIN_AT_BY_USERNAME
)
from utils import utils
from utils.logger import log
from schemas.auth.otp import VerificationRequired
from schemas.auth.login import *
from schemas.auth.token import TokenPair
from .token import (
    generate_token, 
    store_token, 
    verify_token
)
from datetime import datetime, timezone
from services.user import build_user_account
import os

async def init_login(data: LoginRequest, request: Request) -> dict:
    """ Account Login """

    # 1: Verify API Key
    if not verify_api_key(request):
        log.warning(f"Invalid API Key is provided by {data.username}")
        return UNAUTHORIZED
    
    # 2: Get Client IP
    ip = await utils.get_client_real_ip(request)

    # Redis Key
    key = f"Login:InvalidAttempts:{ip}"

    # 3: Check invalid login attempts limit
    if await redis.has_exceeded_limit(key_name = key, attempts_limit = 3):
        log.warning(f"Maximum invalid log in attempts limit reached for {data.username}.")
        return MAX_ATTEMPTS_REACHED
    
    # 4: Validate input format
    if not is_valid_username(data.username) or not is_valid_password(data.password):
        await redis.increment_limit(key_name = key)
        log.warning(f"Invalid credentials are provided by {data.username}.")
        return BAD_REQUEST
    
    try:
        # Acquiring database connection from database pool
        async with database.dbPool.acquire() as conn:

            # Fetching details from database
            row  = await conn.fetchrow(SELECT_USER_DETAILS_BY_USERNAME, data.username)
            log.info(row)
           
            # Checking existence inside database
            if row is None:
                # Username does not exist
                await redis.increment_limit(key_name = key)
                log.warning(f"Invalid credentials are provided by {data.username}.")
                return BAD_REQUEST
            
            # Password verification
            if not verify_password(data.password.encode(), row["password"].encode()):
                await redis.increment_limit(key_name = key)
                log.warning(f"Invalid credentials are provided by {data.username}.")
                return BAD_REQUEST
            
            # Building user details for response
            user_id = int(row["user_id"])
            user = await build_user_account(row, data.username)

            # Check account verification status
            if not row["is_verified"]:
                return VerificationRequired (
                    status_code = 513,
                    message     = "Required verification.",
                    email       = user.email_address,
                )
            
            # Check account two fa status
            if row["two_fa_enabled"]:
                return VerificationRequired (
                    status_code = 513,
                    message     = "Required verification.",
                    email       = user.email_address,
                )

            # Check account active status
            if not row["is_active"]:
                log.error(f"Account access is blocked for {data.username}.")
                return BLOCKED_ACC_ACCESS
            
            # Updating Last Login Field Data
            await conn.execute (
                UPDATE_LAST_LOGIN_AT_BY_USERNAME, 
                datetime.now(timezone.utc), 
                data.username 
            ) 
            
    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return DB_ERROR

    # 5: Reset invalid login attempts after success
    await redis.reset_limit(key_name = key)

    # 6: Generating Access and Refresh Token
    refresh_token = generate_token(user_id, "Refresh")
    access_token  = generate_token(user_id, "Access")

    # 7: Storing Refresh Token in redis
    await store_token(user_id, verify_token(refresh_token), "Refresh")

    log.info(f"Refresh Token: {refresh_token} ")
    log.info(f"Access Token: {access_token}")

    return LoginResponse(
        status_code  = 200,
        message      = "Authentication success.",
        tokens       = TokenPair (
            issued_at                       = int(datetime.now(timezone.utc).timestamp()),
            access_token                    = access_token,
            access_token_expires_in         = int(os.getenv("ACCESS_TOKEN_EXPIRY", "NULL")),
            refresh_token                   = refresh_token,
            refresh_token_expires_in        = int(os.getenv("REFRESH_TOKEN_EXPIRY", "NULL"))
        ),
        user = user
    )
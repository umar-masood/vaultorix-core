from db import database
from db.redis import (
    connect_to_redis,
    has_exceeded_limit,
    increment_limit,
    reset_limit
)
from utils.utils import (
    is_valid_email, 
    is_valid_username, 
    is_valid_password, 
    is_valid_name, 
    verify_api_key,
    hash_password
)
from exceptions.errors import *
from fastapi import Request
from repositories.user import (
    SELECT_EMAIL_BY_EMAIL, 
    INSERT_CREDENTIALS,
    SELECT_USERNAME_BY_USERNAME
)
from utils.utils import *
from utils.logger import log
from typing import Optional
from datetime import datetime
from schemas.auth.register import RegisterRequest
from schemas.common import Response

## Check Username Validatiy and Availability
async def init_check_username(username : str) -> dict:
    if not is_valid_username(username):
        return BAD_REQUEST
    
    try:
        async with database.dbPool.acquire() as conn:        
            row = await conn.fetchrow(
                    SELECT_USERNAME_BY_USERNAME, username
                )

            if row is not None:
                return ALREADY_EXISTS

    except Exception as e:
        log.error("Failed to establish connection with PostgreSQL database.")
        return DB_ERROR
    
    return Response(
        status_code  = 200,
        message      = "Username is available."
    )
    
## Check Email Validatiy and Availability
async def init_check_email(email_address : str) -> dict:
    if not is_valid_email(email_address):
        return BAD_REQUEST
    
    try:
        async with database.dbPool.acquire() as conn:        
            row = await conn.fetchrow(
                    SELECT_EMAIL_BY_EMAIL, email_address
                )

            if row is not None:
                return ALREADY_EXISTS
            
    except Exception as ex:
        log.error("Failed to establish the connection with PostgreSQL database.")
        return DB_ERROR
    
    return Response(
        status_code  = 200,
        message      = "Email address is available."
    )

# Main Method
async def init_register(data: RegisterRequest, request: Request) -> dict:
    # Fetching data
    full_name: str              = data.user.full_name
    username: str               = data.user.username
    email_address: str          = data.user.email
    password: str               = data.user.password
    created_at: datetime        = datetime.fromisoformat(data.user.created_at.replace("Z", "+00:00"))
    last_login: Optional[str]   = data.user.last_login
    is_active: bool             = data.user.is_active
    salt: str                   = data.user.salt

    device_name: str            = data.device_info.device_name
    device_id: str              = data.device_info.device_id
    os_type: str                = data.device_info.os_type
    os_version: str             = data.device_info.os_version
    kernel_version: str         = data.device_info.kernel_version
    
    app_version: str            = data.app_info.version

    # Redis Database Check
    if not await connect_to_redis():
        log.error(f"Failed to connect to the redis.")
        return REDIS_ERROR 

    # 1: API Key verification
    if not verify_api_key(request):
        log.warning(f"Invalid API Key is provided by {username} for signing up.")
        return UNAUTHORIZED
    
    # 2: Getting Client Real IP
    ip = await get_client_real_ip(request)

    # Redis Key
    key =  f"Register:InvalidAttempts:{ip}"

    # 3: Checking Max Invalid Login Attempts
    if await has_exceeded_limit(key_name = key, attempts_limit = 3):
        log.warning(f"Exceeded invalid sign up attempts limit for {username}.")
        return MAX_ATTEMPTS_REACHED
    
    # 5: Data Validation
    if not (
            is_valid_username(username)
        and is_valid_name(full_name)
        and is_valid_email(email_address)
        and is_valid_password(password)
        and is_valid_device_id(device_id)
    ):
        await increment_limit(key_name = key, ex = 24 * 60 * 60)
        log.warning(f"Invalid credentials are provided by {username} for signing up.")
        return BAD_REQUEST

    # 6: Storing data in Database (asyncpg)
    try:
        async with database.dbPool.acquire() as conn:
            async with conn.transaction():

                # Check if email already exists
                row = await conn.fetchrow(SELECT_EMAIL_BY_EMAIL, email_address)
                if row is not None:
                    log.error(f"User already registered {username}.")
                    return ALREADY_EXISTS

                # Prepare data tuple in correct order for INSERT_CREDENTIALS
                details = (
                    full_name, 
                    username, 
                    email_address, 
                    hash_password(password),
                    created_at, 
                    last_login, 
                    is_active,
                    salt,
                    device_name, 
                    device_id, 
                    os_type, 
                    os_version, 
                    kernel_version, 
                    ip, 
                    app_version
                )

                # Execute INSERT (users + devices) in a single transaction
                await conn.execute(INSERT_CREDENTIALS, *details)

    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return DB_ERROR

    # 8: Resetting invalid register attempts
    await reset_limit(key_name = key)
    
    log.info(f"Registration successful of {username}.")

    return Response (
        status_code     = 200,
        message         = "Registration successful."
    )

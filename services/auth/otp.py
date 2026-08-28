from pathlib import Path
from db import database
from db.redis import *
from utils.utils import *
from exceptions.errors import *
from fastapi import BackgroundTasks, Request
from services.user import build_user_account
from redis import RedisError
from repositories.user import ( 
    UPDATE_ACC_VERIFICATION_STATUS_BY_EMAIL,
    SELECT_ID_NAME_BY_EMAIL,
    SELECT_ID_VER_STATUS_BY_EMAIL,
    SELECT_USER_DETAILS_BY_ID
)
from utils.utils import get_client_real_ip
from utils.logger import log
from schemas.auth.otp import (
    SendOTPRequest, 
    VerifyOTPRequest,
    VerifyOTPResponse
)
from schemas.auth.token import TokenPair
from .token import (
    generate_token, 
    store_token, 
    verify_token
)
from datetime import datetime, timezone
import requests, secrets, os, asyncpg

async def check_existing_user(key_name: str) -> bool:
    """
    This function checks whether the user exists by otp attempts key inside Redis.
    Redis returns:
    1 -> key exists
    0 -> key does not exist
    """
    return await redis_conn.exists(key_name) == 1

async def add_user(key_name: str) -> None:
    """
    This function adds user in redis by setting max otp attempts key value to 1 with expiry of 24 hrs.
    This key acts as a counter initializer for OTP attempt tracking.
    """
    await redis_conn.set(key_name, 1, ex = 24 * 60 * 60)

def generate_otp() -> str:
    """
    This function generates a random 5 digits otp from a character set.
    Character set and OTP length are configurable through environment variables.
    """
    return ''.join(
        secrets.choice(os.getenv("OTP_CHARS", "NULL"))
        for _ in range(int(os.getenv("OTP_LENGTH", "NULL")))
    )

async def store_otp(user_id: str, otp: str) -> None:
    """
    This function stores the current generated otp inside Redis database.
    OTP is stored for a short period of time (120 seconds) for security reasons.
    """
    otp_key = f"{user_id}:OTP:CurrentOTP"
    await redis_conn.set(otp_key, otp, ex = 120)

# OTP Email Setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
EMAIL_TEMPLATE = Path(BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")

headers = {
    "api-key"       : os.getenv("BREVO_API_KEY"),
    "content-type"  : "application/json",
    "accept"        : "application/json"
}

def prepare_html_email_template(name: str, otp: str) -> str:
    """
    This function prepares the html email template with user name and otp.
    Returns a formatted html template as string
    """
    return EMAIL_TEMPLATE.format(NAME = name, OTP = otp)

def send_email(data: dict) -> bool:
    """
    This function sends the email to the user after receiving the email template with data.
    Returns True if it is sent otherwise False
    """
    try:
        resp = requests.post(
            os.getenv("BREVO_URL", "NULL"),
            json = data,
            headers = headers
        )

        return resp.status_code in (200, 201)

    except Exception as ex:
        log.error(f'Error in sending OTP to the user: {ex}')
        return False

def prepare_otp_email(html_content: str, receiver_name: str, receiver_email: str) -> bool:
    """
    This function prepares the email with user and organization detials. After this the email send to the user
    Returns True if it goes well otherwise False
    """

    data = {
        "sender": {
            "name"  : "Vaultorix",
            "email" : "support@umarcreations.site"
        },

        "to": [{
            "email" : receiver_email,
            "name"  : receiver_name
        }],

        "subject"     : "Your One Time Password for Vaultorix",
        "htmlContent" : html_content
    }

    return send_email(data)

# Main Methods
## Send OTP
async def init_sendOtp(
    data: SendOTPRequest,
    request: Request,
    background_tasks : BackgroundTasks
) -> dict:

    # 1. Validate API Key
    if not verify_api_key(request):
        log.warning(f"Wrong API Key is provided by {data.email} to send otp.")
        return UNAUTHORIZED

    # 2. Validate Fields
    if not is_valid_email(data.email):
        log.warning(f"Credentials are in invalid format provided by user {data.email}.")
        return BAD_REQUEST

    # 3. Redis connection check MUST happen before any Redis call
    if not await connect_to_redis():
        log.error(f"Failed to connect to the Redis")
        return REDIS_ERROR 

    # 4. Get client IP & rate limit
    ip = await get_client_real_ip(request)

    # Redis Keys
    key_1 = f'OTP:Requests:{ip}'    # OTP Requests based on IP Address
    key_2 = "OTP:MaxOTPAttempts"    # OTP Requests based on User id

    try:
        # Increment IP request counter
        await increment_limit(
            key_name = key_1,
            ex = 24 * 60 * 60
        )

        # Check if request limit exceeded
        if await has_exceeded_limit(
            key_name = key_1,
            attempts_limit = 3
        ):
            log.error(f"IP is blocked for attempting to send OTP to {data.email}.")
            return TOO_MANY_REQUESTS

    except RedisError as re:
        log.error(f"Redis database error : {re}")
        return REDIS_ERROR

    # 6. Getting user_id, user full name from database
    user_id : int
    full_name : str

    try:
        async with database.dbPool.acquire() as conn:

            row = await conn.fetchrow(
                SELECT_ID_NAME_BY_EMAIL,
                data.email
            )

            user_id = int(row["user_id"])
            full_name = row["full_name"]

    except Exception as ex:
        log.error(f"PostgreSQL database error : {ex}")

    # 5. Handle user attempt limits safely
    try:
        user_key = f"{user_id}:{key_2}"

        if not await check_existing_user(key_name = user_key):
            await add_user(key_name = user_key)
        else:
            if await has_exceeded_limit(
                user_id = user_id,
                key_name = key_2,
                attempts_limit = 3
            ):
                log.warning(f"Maximum OTP attempts limit reached for {data.email}.")
                return MAX_ATTEMPTS_REACHED

    except RedisError as re:
        log.error(f"Redis database error : {re}")
        return REDIS_ERROR


    # 6. Generate OTP + Store
    otp = generate_otp()

    log.info(f"Generated OTP is {otp}")

    try:
        # Store OTP temporarily
        await store_otp(user_id, otp)

        # Increment user attempt counter
        await increment_limit(
            user_id = user_id,
            key_name = key_2,
            ex = 24 * 60 * 60
        )

    except RedisError as re:
        log.error(f"Redis database error : {re}")
        return REDIS_ERROR


    # 7. Prepare email
    try:
        email_html = prepare_html_email_template(full_name, otp)

        if not email_html:
            log.error("Failed to prepare the OTP email template.")
            return EMAIL_TEMPLATE_ERROR

    except Exception as ex:
        log.error(f"Failed to prepare the OTP email template: {ex}")
        return EMAIL_TEMPLATE_ERROR


    # 8. Send OTP email asynchronously
    background_tasks.add_task(
        prepare_otp_email,
        email_html,
        full_name,
        data.email
    )

    log.info(f"OTP sent successfully to {data.email}.")

    return {
        "status_code": 200,
        "message": "Your request has been processed."
    }

## Verify OTP
## Verify OTP
async def init_verifyOtp(data: VerifyOTPRequest, 
                         request: Request) -> dict:

    # 1: Validate API Key
    if not verify_api_key(request):
        log.warning(f"Invalid API Key provided by {data.email} for verifying OTP.")
        return UNAUTHORIZED

    # 2: Ensure Redis connection
    if not await connect_to_redis():
        log.error("Redis connection could not be established.")
        return OTP_VERIFY_FAILED

    # Redis Key for invalid verification attempts
    key_invalid = "OTP:InvalidVerifyAttempts"

    # 3: Fetch user_id and current verification status from DB
    user_id: int
    is_verified: bool

    try:
        async with database.dbPool.acquire() as conn:

            row = await conn.fetchrow(
                SELECT_ID_VER_STATUS_BY_EMAIL,
                data.email
            )

            if not row:
                log.warning(f"User not found for email: {data.email}")
                return OTP_VERIFY_FAILED

            user_id = int(row["user_id"])
            is_verified = row["is_verified"]

    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return OTP_VERIFY_FAILED


    # 4: Check if invalid OTP attempts already exceeded
    try:
        if await has_exceeded_limit(
            user_id   = user_id,
            key_name  = key_invalid,
            attempts_limit = 5
        ):
            log.warning(f"Maximum OTP verification attempts reached for {data.email}.")
            return MAX_ATTEMPTS_REACHED

    except RedisError as re:
        log.error(f"Redis database error: {re}")
        return REDIS_ERROR


    # 5: Fetch stored OTP from Redis
    otp_key = f"{user_id}:OTP:CurrentOTP"
    stored_otp = await redis_conn.get(otp_key)


    # 6: Compare OTP
    if stored_otp and secrets.compare_digest(stored_otp, data.otp):
        try:
            async with database.dbPool.acquire() as conn:
                # Update verification status if not already verified
                if not is_verified:
                    await conn.execute(
                        UPDATE_ACC_VERIFICATION_STATUS_BY_EMAIL,
                        data.email
                    )

                # If login type provided → generate tokens
                if data.auth_type is not None:
                    if data.auth_type.lower() in ("login", "signin"):

                        # Generating tokens
                        refresh_token = generate_token(user_id, "Refresh")
                        access_token  = generate_token(user_id, "Access")

                        # Storing Refresh Token in redis
                        await store_token(user_id, verify_token(refresh_token), "Refresh")

                        # Retrieving user data
                        row = await conn.fetchrow(
                            SELECT_USER_DETAILS_BY_ID,
                            user_id
                        )

                        user = await build_user_account(row, row["username"])

                        # Remove OTP + reset counters
                        await redis_conn.delete(otp_key)
                        await reset_limit(user_id=user_id, key_name="OTP:MaxOTPAttempts")
                        await reset_limit(user_id=user_id, key_name=key_invalid)
                        await reset_limit(key_name=f"OTP:Requests:{await get_client_real_ip(request)}")

                        log.info(f"OTP verified successfully for {data.email}.")

                        return VerifyOTPResponse (
                            isVerified = True,
                            tokens = TokenPair (
                                issued_at                       = int(datetime.now(timezone.utc).timestamp()),
                                access_token                    = access_token,
                                access_token_expires_in         = int(os.getenv("ACCESS_TOKEN_EXPIRY", "NULL")),
                                refresh_token                   = refresh_token,
                                refresh_token_expires_in        = int(os.getenv("REFRESH_TOKEN_EXPIRY", "NULL"))
                            ),
                            user = user
                        )

            # If not login flow → simple success response

            await redis_conn.delete(otp_key)
            await reset_limit(user_id=user_id, key_name="OTP:MaxOTPAttempts")
            await reset_limit(user_id=user_id, key_name=key_invalid)
            await reset_limit(key_name=f"OTP:Requests:{await get_client_real_ip(request)}")

            log.info(f"OTP verified successfully for {data.email}.")

            return VerifyOTPResponse (
                isVerified = True
            )

        except asyncpg.PostgresError as ex:
            log.error(f"SQLSTATE: {getattr(ex, 'sqlstate', None)}")
            log.error(f"MESSAGE: {ex}")
            log.error(f"DETAIL: {getattr(ex, 'detail', None)}")
            log.error(f"HINT: {getattr(ex, 'hint', None)}")
            # log.error(f"Error updating verification status: {ex}")
            return OTP_VERIFY_FAILED


    # 7: OTP mismatch — increment invalid attempts
    try:
        await increment_limit(
            user_id = user_id,
            key_name = key_invalid,
            ex = 15 * 60  
        )

    except RedisError as re:
        log.error(f"Redis database error: {re}")
        return REDIS_ERROR


    log.warning(f"OTP verification failed for {data.email}.")
    return OTP_VERIFY_FAILED
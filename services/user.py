from utils.logger import log
from schemas.common import Response
from schemas.user import PasswordChange, UserAccount
from services.auth.token import validate_token, get_token
from utils.utils import *
from exceptions.errors import *
from typing import Annotated
from fastapi import Depends, Request, UploadFile, File
from db import database
from db.redis import redis_conn, connect_to_redis
from repositories.user import (
    UPDATE_TWO_FA_STATUS_BY_ID,
    UPDATE_USERNAME_BY_ID,
    SELECT_PASSWORD_BY_ID,
    UPDATE_PASSWORD_BY_ID,
    DELETE_ACCOUNT_RETURN_PROFILE_PICTURE_PATH_BY_ID,
    UPDATE_RETURN_PROFILE_PICTURE_PATH_BY_ID,
    DELETE_PROFILE_PICTURE_PATH_AND_RETURN_BACK_BY_ID,
)
from supabase import create_async_client
from uuid import uuid4
from typing import Optional
import os

async def build_user_account(row, username: Optional[str]) -> UserAccount:
    email_address   = row["email_address"]
    full_name       = row["full_name"]
    user_id         = int(row["user_id"])
    two_fa_enabled  = row["two_fa_enabled"]
    salt            = row["salt"]

    if username is None:
        username = row["username"]
        
    # Avatar
    picture_path: str = None
    if row["profile_picture"]:
        picture_filename = row["profile_picture"]
        picture_path = f"https://gkayoonjfgydserlgdwk.supabase.co/storage/v1/object/public/avatars/{picture_filename}"

    # Username change check
    exists = await redis_conn.exists(f"{user_id}:Account:NotAllowedToChangeUsername")                
    if exists:
        allowed_to_change_username = False
    else:
        allowed_to_change_username = True

    return UserAccount(
        full_name                   = full_name,
        email_address               = email_address,
        username                    = username,
        avatar_url                  = picture_path if picture_path else None,
        is_two_factor_enabled       = two_fa_enabled,
        allowed_to_change_username  = allowed_to_change_username,
        salt                        = salt
    )

async def get_authenticated_user_id(token: str) -> int | None:
    """
    Validate access token and return authenticated user id
    """

    payload = await validate_token(token, "Access")

    if payload is None:
        return None

    return int(payload["sub"])

async def get_supabase():
    """
    Returns Supabase async client
    """

    return await create_async_client(
        supabase_url=os.getenv("SUPABASE_URL", "NULL"),
        supabase_key=os.getenv("SERVICE_KEY", "NULL")
    )

async def delete_profile_picture_from_storage(supabase, profile_picture_path: str ) -> bool:
    """
    Delete profile picture from Supabase storage
    """

    if not profile_picture_path:
        return True

    try:
        response = await supabase.storage.from_("avatars").remove(
            [profile_picture_path]
        )

        log.info(response)
        return True

    except Exception as ex:
        log.error(f"Failed to delete profile picture: {ex}")
        return False

async def init_two_fa_enabled(is_enabled: bool = False, token: Annotated[str, Depends(get_token)] = None ) -> dict:

    """
    Enable/Disable Two Factor Authentication on each sign in to account
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)

    if user_id is None:
        return UNAUTHORIZED

    # Checking Redis Connection
    if not await connect_to_redis():
        return REDIS_ERROR

    # Redis Key
    key = f"{user_id}:Account:TwoFactorAuthEnabled"

    # Getting current value
    value = await redis_conn.get(key)

    if value is None:
        value = 0

    value = bool(int(value))


    log.info(f"is_enabled = {is_enabled}, type = {type(is_enabled)}")
    log.info(f"Redis raw value = {await redis_conn.get(key)}")
    log.info(f"Redis bool value = {value}")

    # Checking whether same value already exists
    if value == is_enabled:
        log.info(f"User {user_id} is trying to update the Two FA status with same value")

    else:
        # Updating Redis
        await redis_conn.set(key, int(is_enabled))

        try:
            # Updating Database
            async with database.dbPool.acquire() as conn:
                await conn.execute(
                    UPDATE_TWO_FA_STATUS_BY_ID,
                    is_enabled,
                    user_id
                )

        except Exception as ex:
            log.error(f"PostgreSQL error when updating Two FA status: {ex}")
            return DB_ERROR

    return Response(
        status_code = 200,
        message     = "Your request has been processed."
    )

async def init_change_username(username: str = None, token: Annotated[str, Depends(get_token)] = None) -> dict:
    """
    Changes the username of user account
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)

    if user_id is None:
        return UNAUTHORIZED

    # Validating Username
    if not is_valid_username(username):
        return BAD_REQUEST

    # Checking Redis Connection
    if not await connect_to_redis():
        return REDIS_ERROR

    # Redis Key
    key = f"{user_id}:Account:NotAllowedToChangeUsername"

    # Checking whether username can be changed
    value = await redis_conn.get(key)

    if value is not None:
        log.info(f"We cannot change the username of {user_id}")
        return BAD_REQUEST

    try:
        # Updating username inside database
        async with database.dbPool.acquire() as conn:
            await conn.execute(
                UPDATE_USERNAME_BY_ID,
                username,
                user_id
            )

    except Exception as ex:
        log.error(f"PostgreSQL error when updating username: {ex}")
        return DB_ERROR

    # Setting cooldown
    await redis_conn.set(
        key,
        "",
        ex = 30 * 24 * 60 * 60
    )

    return Response(
        status_code = 200,
        message     = "Your request has been processed."
    )

async def init_change_password(data: PasswordChange, token: Annotated[str, Depends(get_token)] = None) -> dict:
    """
    Change the old password with new password
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)

    if user_id is None:
        return UNAUTHORIZED

    # Passwords
    old_password: str = data.old_password
    new_password: str = data.new_password

    # Validating passwords
    if not is_valid_password(old_password):
        log.error("Old password is not valid.")
        return BAD_REQUEST

    if not is_valid_password(new_password):
        log.error("New password is not valid.")
        return BAD_REQUEST

    try:
        async with database.dbPool.acquire() as conn:

            # Getting current password
            row = await conn.fetchrow(
                SELECT_PASSWORD_BY_ID,
                user_id
            )

            if row is None:
                return BAD_REQUEST

            # Verifying old password
            if not verify_password(
                old_password.encode(),
                row["password"].encode()
            ):
                log.error("Password does not match")
                return BAD_REQUEST

            # Updating password
            await conn.execute(
                UPDATE_PASSWORD_BY_ID,
                hash_password(new_password),
                user_id
            )

    except Exception as ex:
        log.error(f"PostgreSQL error when changing password: {ex}")
        return DB_ERROR

    return Response(
        status_code = 200,
        message     = "Your request has been processed."
    )

async def init_delete_account(request: Request, token: Annotated[str, Depends(get_token)] = None) -> dict:
    """
    Delete user account permanently
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)

    if user_id is None:
        return UNAUTHORIZED

    # Checking Redis Connection
    if not await connect_to_redis():
        return REDIS_ERROR

    # Getting Client Real IP
    ip = await get_client_real_ip(request)

    # Delete all related Redis keys
    await redis_conn.delete(
        f"{user_id}:BugReport:MaxLimit",
        f"{user_id}:AppUpdate:MaxCheckUpdateLimit",
        f"{user_id}:Account:NotAllowedToChangeUsername",
        f"{user_id}:Account:TwoFactorAuthEnabled",
        f"{user_id}:OTP:MaxOTPAttempts",
        f"{user_id}:RefreshTokenAttempts",
        f"{user_id}:OTP:CurrentOTP",
        f"{user_id}:OTP:InvalidVerifyAttempts",
        f"{user_id}:AcessToken",
        f"{user_id}:RefreshToken",
        f"OTP:Requests:{ip}",
        f"Login:InvalidAttempts:{ip}",
        f"Register:InvalidAttempts:{ip}",
    )

    try:
        async with database.dbPool.acquire() as conn:

            # Deleting account
            row = await conn.fetchrow(
                DELETE_ACCOUNT_RETURN_PROFILE_PICTURE_PATH_BY_ID,
                user_id
            )

            if row is None:
                return BAD_REQUEST

            # Removing profile picture from storage
            deleted_profile_picture = row["deleted_profile_picture"]

            if deleted_profile_picture:
                supabase = await get_supabase()

                success = await delete_profile_picture_from_storage(
                    supabase,
                    deleted_profile_picture
                )

                if not success:
                    return DB_ERROR

    except Exception as ex:
        log.error(f"PostgreSQL error: {ex}")
        return DB_ERROR

    return Response (
        status_code = 200,
        message     = "Your request has been processed."
    )

async def init_delete_profile_picture(token: Annotated[str, Depends(get_token)] = None) -> dict:
    """
    Deletes the profile picture of user account
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)

    if user_id is None:
        return UNAUTHORIZED

    try:
        async with database.dbPool.acquire() as conn:

            # Removing profile picture path from database
            row = await conn.fetchrow(
                DELETE_PROFILE_PICTURE_PATH_AND_RETURN_BACK_BY_ID,
                user_id
            )

            if row is None:
                return BAD_REQUEST

            deleted_profile_picture = row["deleted_profile_picture"]

            if deleted_profile_picture:
                supabase = await get_supabase()

                success = await delete_profile_picture_from_storage(
                    supabase,
                    deleted_profile_picture
                )

                if not success:
                    return DB_ERROR

    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return DB_ERROR

    log.info(f"Profile picture has been deleted by {user_id}.")

    return Response(
        status_code = 200,
        message     = "Your request has been processed."
    )

async def init_change_profile_picture(picture: UploadFile = File(None), token: Annotated[str, Depends(get_token)] = None) -> dict:
    """
    Changes the profile picture of user account
    """

    # Validating Token
    user_id = await get_authenticated_user_id(token)
    if user_id is None:
        return UNAUTHORIZED

    # Checking uploaded file
    if picture is None:
        return BAD_REQUEST

    # Creating Supabase Client
    supabase = await get_supabase()

    # File Extension
    file_ext = os.path.splitext(picture.filename)[1]

    # New Profile Picture Path
    profile_picture_path = str(uuid4()) + file_ext

    try:
        # Uploading picture
        response = await supabase.storage.from_("avatars").upload(
            path = profile_picture_path,
            file = await picture.read(),
            file_options = {
                "content_type": picture.content_type
            }
        )

        log.info(response)

    except Exception as ex:
        log.error(f"Failed to upload profile picture: {ex}")
        return DB_ERROR

    try:
        async with database.dbPool.acquire() as conn:
            # Setting new profile picture path and getting old profile picture path
            old_row = await conn.fetchrow( 
                UPDATE_RETURN_PROFILE_PICTURE_PATH_BY_ID, 
                user_id, 
                profile_picture_path 
            )

            old_profile_picture = None

            if old_row is not None:
                old_profile_picture = old_row["old_profile_picture"]

    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return DB_ERROR

    # Deleting old profile picture
    if old_profile_picture:
        await delete_profile_picture_from_storage(
            supabase,
            old_profile_picture
        )

    log.info(f"Profile picture has been updated by {user_id}.")

    return Response(
        status_code = 200,
        message     = "Your request has been processed."
    )
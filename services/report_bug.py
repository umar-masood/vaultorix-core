from schemas.common import Response
from exceptions.errors import *
from services.auth.token import validate_token, get_token
from fastapi import UploadFile, File, Depends, Form
from typing import Annotated
from db import database
from db.redis import (
    has_exceeded_limit,
    increment_limit
)
from utils.logger import log
from supabase import create_async_client
from repositories.bug_report import INSERT_BUG_REPORT_DETAILS
from uuid import uuid4
from datetime import datetime, timezone
import os

async def init_report_bug(
        subject: str = Form(...),
        description: str = Form(...),
        app_version: str = Form(...),
        screenshot: UploadFile = File(None), 
        token : Annotated[str, Depends(get_token)] = None
    ) -> dict:

    # Validating Access Token
    payload = await validate_token(token, "Access")
    if not payload:
        return BAD_REQUEST
    
    # Data Validation
    if len(subject) < 20 or len(description) < 40:
        return BAD_REQUEST
    
    if len(subject) > 200 or len(description) > 1000:
        return BAD_REQUEST

    # Extracting user id from token payload
    user_id = int(payload["sub"])

    # Redis Key
    key = "BugReport:MaxLimit"

    # Checking max limit of reporting a bug
    if await has_exceeded_limit(user_id = user_id, key_name = key, attempts_limit = 3):
        return MAX_ATTEMPTS_REACHED
    
    # If screenshot uploaded by user, 
    screenshot_path : str = ""
    if screenshot:
        # Storing screenshot in cloud
        supabase = await create_async_client(
            supabase_url = os.getenv("SUPABASE_URL", "NULL"),
            supabase_key = os.getenv("SERVICE_KEY", "NULL")
        )

        # File Extension
        file_ext = os.path.splitext(screenshot.filename)[1]

        # Screenshot Path
        screenshot_path = str(uuid4()) + file_ext

        try:
            # Uploading screenshot
            response = await supabase.storage.from_('Bug-Reports-Screenshots').upload(
                path = screenshot_path,
                file = await screenshot.read(),
                file_options = {"content_type" : screenshot.content_type}
            )

        except Exception as ex:
            log.error(f"Failed to upload screenshot: {ex}")
            return DB_ERROR

        log.info(response)

    # Saving Bug Report Metadata into Database
    try:
        async with database.dbPool.acquire() as conn:
            await conn.execute( 
                INSERT_BUG_REPORT_DETAILS,
                user_id,
                subject,
                description,
                screenshot_path,
                datetime.now(timezone.utc),
                app_version,
                "In progress"
            )

    except Exception as ex:
        log.error(f"PostgreSQL database error: {ex}")
        return DB_ERROR

    # Incrementing reporting attempt limit
    await increment_limit(user_id = user_id, key_name = key, ex = 15 * 60)

    log.info(f'Bug reported submitted successfully by {user_id}.')

    return Response(
        status_code   = 200,
        message       = "Bug report has been submitted."
    )
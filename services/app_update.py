from supabase import create_async_client
from utils.logger import log
from schemas.app.update import UpdateAvailableResponse
from schemas.common import Response
from services.auth.token import validate_token, get_token
from exceptions.errors import (
    BAD_REQUEST,
    MAX_ATTEMPTS_REACHED
)
from typing import Annotated
from fastapi import Depends
from db.redis import (
    has_exceeded_limit, 
    increment_limit
)
import os
import json

def version_tuple(version : str) -> tuple:
    return tuple(int(x) for x in version.split("."))

async def init_check_app_update(current_version : str, 
                                token : Annotated[str, Depends(get_token)] = None
                                ) -> dict:
    """
    This method checks whether there is a new version of application is available:
    
    In case if there is an update available, it will returns the download link along with update metadata back to the client otherwise return no update response.

    Update Metadata:
    - latest_version : VERSION,
    - file_size : SIZE_IN_BYTES,
    - download_url : URL,
    - release_notes : NOTES,
    - release_date : DATE

    """
    # Validating Access Token
    payload = await validate_token(token, "Access")
    if not payload:
        return BAD_REQUEST
    
    # Extracting user id from token payload
    user_id = int(payload["sub"])

    # Redis Key
    key = "AppUpdate:MaxCheckUpdateLimit"

    # Checking max limit of checking for app updates
    if await has_exceeded_limit(user_id = user_id, key_name = key, attempts_limit = 5):
        return MAX_ATTEMPTS_REACHED
    
    # Fetching version file data
    supabase = await create_async_client(
        supabase_url = os.getenv("SUPABASE_URL", "NULL"),
        supabase_key = os.getenv("SERVICE_KEY", "NULL")
    )

    response = await supabase.storage.from_("App-Files").download(
        path = "version.json"
    )

    # Loading into JSON
    data = json.loads(response)
    log.info(data)

    # Latest Version
    latest_version : str = data['latest_version']

    # Incrementing update attempt limit
    await increment_limit(user_id = user_id, key_name = key, ex = 5 * 60);

    # Version Comparison
    if (version_tuple(latest_version) > version_tuple(current_version)):
        return UpdateAvailableResponse(
            latest_version  = latest_version,
            file_size       = data['file_size'],
            download_url    = data['download_url'],
            release_notes   = data['release_notes'],
            release_date    = data['release_date'] 
        )
    
    else:

        return Response (
            status_code = 200,
            message = "You are up to date."  
        )


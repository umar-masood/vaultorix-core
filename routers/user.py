from fastapi import Depends, APIRouter
from schemas.common import Response
from services.auth.register import init_check_email, init_check_username
from services.user import *

user_router = APIRouter(prefix = "/user", tags = ["User"])

# Checking Availability of Unique Username
@user_router.get('/check-username/{username}', response_model = Response)
async def check_username(result : dict = Depends(init_check_username)) -> dict:
   return result

# Checking Availability of Email Address 
@user_router.get('/check-email/{email_address}', response_model = Response)
async def check_email(result : dict = Depends(init_check_email)) -> dict:
   return result

## User Settings
@user_router.put('/account/update-2fa/{is_enabled}', response_model = Response)
async def update_2fa(result : dict = Depends(init_two_fa_enabled)) -> dict:
    return result

@user_router.put('/account/update-username/{username}', response_model = Response)
async def update_2fa(result : dict = Depends(init_change_username)) -> dict:
    return result

@user_router.post('/account/update-password', response_model = Response)
async def update_2fa(result : dict = Depends(init_change_password)) -> dict:
    return result

@user_router.delete('/account/delete', response_model = Response)
async def delete_account(result : dict = Depends(init_delete_account)) -> dict:
    return result

@user_router.post('/account/update-profile-picture', response_model = Response)
async def delete_account(result : dict = Depends(init_change_profile_picture)) -> dict:
    return result

@user_router.delete('/account/profile-picture/delete', response_model = Response)
async def delete_profile_picture(result : dict = Depends(init_delete_profile_picture)) -> dict:
    return result
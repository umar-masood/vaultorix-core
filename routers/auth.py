from fastapi import Depends, APIRouter
from typing import Union

from schemas.common import Response
from schemas.auth.otp import VerificationRequired, VerifyOTPResponse
from schemas.auth.refresh import RefreshTokenResponse
from schemas.auth.login import LoginResponse

from services.auth.refresh import init_refresh
from services.auth.otp import init_sendOtp, init_verifyOtp
from services.auth.register import init_register
from services.auth.login import init_login
from services.auth.logout import init_logout

auth_router = APIRouter(prefix = "/auth", tags = ["Authentication"])

# Send OTP
@auth_router.post('/otp/send', response_model = Response)
async def send_otp(result : dict = Depends(init_sendOtp)) -> dict:
    return result
    
# Verify OTP
@auth_router.post('/otp/verify', response_model = Union[VerifyOTPResponse, Response])
async def verify_otp(result : dict = Depends(init_verifyOtp)) -> dict:
    return result

# Account Login
@auth_router.post('/login', response_model = Union[Response, VerificationRequired, LoginResponse])
async def verify_credentials(result : dict = Depends(init_login)) -> dict:
    return result

# Account Register
@auth_router.post('/register', response_model = Union[Response])
async def store_credentials(result : dict = Depends(init_register)) -> dict:
   return result

# Account Logout
@auth_router.post('/logout', response_model = Response)
async def account_logout(result = Depends(init_logout)) -> dict:
    return result

# Refreshing Access Token 
@auth_router.post('/refresh', response_model = Union[RefreshTokenResponse, Response])
async def refresh(result = Depends(init_refresh)) -> dict:
    return result


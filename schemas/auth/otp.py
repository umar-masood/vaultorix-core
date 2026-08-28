from pydantic import BaseModel
from typing import Optional
from .token import TokenPair
from schemas.user import UserAccount

class SendOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    auth_type : Optional[str] = None

class VerifyOTPResponse(BaseModel):
    isVerified: bool
    tokens: Optional[TokenPair] = None
    user: Optional[UserAccount] = None

class VerificationRequired(BaseModel): 
    status_code : int 
    message : str 
    email : str
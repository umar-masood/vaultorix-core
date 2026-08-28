from pydantic import BaseModel
from .token import TokenPair
from schemas.user import UserAccount

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status_code : int
    message: str
    tokens: TokenPair
    user: UserAccount

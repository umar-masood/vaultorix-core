from pydantic import BaseModel
from typing import Optional

class PasswordChange(BaseModel):
    old_password : str
    new_password : str

class UserAccount(BaseModel):
    full_name: str
    username: str
    email_address: str

    avatar_url: Optional[str] = None

    is_two_factor_enabled: bool
    allowed_to_change_username: bool

    salt: str
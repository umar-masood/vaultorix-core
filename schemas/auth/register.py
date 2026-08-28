from pydantic import BaseModel
from schemas.device import DeviceInfo
from schemas.app.app import AppInfo
from typing import Optional

class RegisterUserInput(BaseModel):
    full_name: str
    username: str
    email: str
    password: str
    salt: str

    created_at : str
    is_active : bool
    last_login : Optional[str] = None

class RegisterRequest(BaseModel):
    user: RegisterUserInput
    device_info: DeviceInfo
    app_info: AppInfo

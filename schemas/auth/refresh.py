from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token            : str
    access_token_expires_in : int
    issued_at               : int
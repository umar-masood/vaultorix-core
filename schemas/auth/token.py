from pydantic import BaseModel

class TokenPair(BaseModel):
    access_token                : str
    access_token_expires_in     : int
    refresh_token               : str
    refresh_token_expires_in    : int
    issued_at                   : int
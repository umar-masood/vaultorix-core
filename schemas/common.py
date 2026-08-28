from pydantic import BaseModel

# Response Model
class Response(BaseModel):
    status_code : int
    message : str
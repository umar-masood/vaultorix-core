from pydantic import BaseModel

class AppInfo(BaseModel):
    version : str
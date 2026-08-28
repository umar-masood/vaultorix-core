from pydantic import BaseModel

class UpdateAvailableResponse(BaseModel):
    latest_version : str
    file_size : int
    download_url : str
    release_notes : str
    release_date : str

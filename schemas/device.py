from pydantic import BaseModel

class DeviceInfo(BaseModel):
    device_name : str
    device_id : str
    os_type : str
    os_version : str
    kernel_version : str
from fastapi import Depends, APIRouter
from schemas.common import Response
from services.report_bug import init_report_bug
from typing import Annotated
from schemas.app.update import UpdateAvailableResponse
from services.app_update import init_check_app_update

app_router = APIRouter(prefix = "/app", tags = ["App"])

@app_router.post("/report-bug", response_model = Response)
async def report_bug(result : Annotated[dict, Depends(init_report_bug)]) -> dict:
    return result

@app_router.get('/check-update/{current_version}', response_model = Response | UpdateAvailableResponse)
async def check_app_update(result : Annotated[dict, Depends(init_check_app_update)]) -> dict:
    return result
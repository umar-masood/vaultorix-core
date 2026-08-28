from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import database
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from routers.auth import auth_router
from routers.user import user_router
from routers.app import app_router

# Loads .env
load_dotenv()

# Startup Event
@asynccontextmanager
async def lifespan(app : FastAPI):
    await database.init_database()
    yield
    await database.dbPool.close()
    
# FastAPI Setup
app = FastAPI(title = "Vaultorix", lifespan = lifespan, 
              swagger_ui_parameters = {"defaultModelsExpandDepth": -1})

# Root
@app.get("/", response_class = HTMLResponse)
async def root() -> HTMLResponse:
    html_content = """
    <html>
        <head>
            <title>Forbidden</title>
        </head>
        <body>
            <h1></h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=404)

## Auth Router
app.include_router(auth_router)

## Users Router
app.include_router(user_router)

## App Router
app.include_router(app_router)
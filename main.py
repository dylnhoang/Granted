from fastapi import FastAPI
from backend.routers import match_grants

app = FastAPI()
app.include_router(match_grants.router)
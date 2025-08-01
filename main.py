from fastapi import FastAPI
from backend.routers import profile, match_grants, auth

app = FastAPI()

app.include_router(profile.router)
app.include_router(match_grants.router)
app.include_router(auth.router)
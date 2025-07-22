from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from supabase import create_client
from dotenv import load_dotenv
import os

from backend.services.score_grant import score_grant

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

class UserProfile(BaseModel):
    user_type: str
    location: str
    major: str
    race: str
    interests: List[str]

@router.post("/match-grants")
def match_grants(user: UserProfile):
    grants = supabase.table("grants").select("*").execute().data
    scored = []
    for grant in grants:
        score = score_grant(user.dict(), grant)
        if score > 0:
            grant["score"] = score
            scored.append(grant)
    return sorted(scored, key=lambda g: g["score"], reverse=True)
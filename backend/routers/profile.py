from fastapi import APIRouter, Depends, HTTPException, Header, Body
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
router = APIRouter()

def get_user_from_token(token: str):
    try:
        return supabase.auth.get_user(token)["user"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
@router.get("/me")
def get_profile(authorization: str = Header(...)):
    token = authorization.split("Bearer ")[-1]
    user = get_user_from_token(token)
    user_id = user["id"]

    res = supabase.table("profiles").select("*").eq("id", user_id).single().execute
    if res.data:
        return res.data
    else:
        raise HTTPException(status_code=404, detail="Profile not found")
    
@router.post("/profile/update")
def update_profile(full_name: str = Body(...), authorization: str = Header(...)):
    token = authorization.split("Bearer ")[-1]
    user = get_user_from_token(token)
    user_id = user["id"]

    res = supabase.table("profiles").upsert({
        "id": user_id,
        "full_name": full_name,
    }).execute()

    return {"message": "Profile updated", "profile": res.data}

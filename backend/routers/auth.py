from fastapi import APIRouter, HTTPException, Body
from pydantic import EmailStr
from supabase import create_client
from gotrue.errors import AuthApiError
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
router = APIRouter()

@router.post('/signup')
def signup(email: str = Body(...), password: str = Body(...)):
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
        print("SUPABASE SIGNUP RESULT:", result)

        return {"message": "Check your email to confirm registration", "user": str(result.user)}

    except Exception as e:
        print("Signup Error:", str(e))
        raise HTTPException(status_code=500, detail="Signup failed.")



@router.post('/login')
def login(email: str = Body(...), password: str = Body(...)):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        print("SUPABASE LOGIN RESULT:", result)

        return {
            "access_token": result.session.access_token,
            "user": str(result.user)
        }

    except Exception as e:
        print("Login Error:", str(e))
        raise HTTPException(status_code=401, detail="Invalid login credentials.")

